"""
High level setup:
Sacred (https://sacred.readthedocs.io/en/latest/) is used to configure, run, save the experiments.
Please read the docs, otherwise the code below won't make much sense.
In short: @ex.config changes configuration of experiment, @ex.command and @ex.capture
makes configuration available and @ex.automain is the entry point of the program.

To start an experiment:
python main.py -p with environment.config_file=<environment_name>.yaml [... more configuration]

For example

python main.py -p with environment.config_file=openaiEnv.yaml seed=1 ...

+++ environment.config_file MUST be specified in command line, other parameters are optional +++

Which environment to run is configured by environment.config_file=<environment_name>.yaml.
The corresponding yaml file (in code/conf) contains all required info/config for the environment and
additional model specific information (like what the encoder/decoder architecture should be).

Configuration happens in 4 places:
- code/conf/default.yaml: The default values
- code/conf/<env_name>.yaml: Specifies the environment and
                             updates the model config with environment specific values
- The command line (overrides everything when specified)
- The general_config() function below updates some values

To use DVRL, set algorithm.use_particle_filter=True, for RNN set it to False.
"""

import collections
import logging
import multiprocessing
import os
import sys
import time

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from baselines.common.vec_env.dummy_vec_env import DummyVecEnv
from baselines.common.vec_env.subproc_vec_env import SubprocVecEnv
from baselines.common.vec_env.vec_normalize import VecNormalize
from gym.envs.registration import register
from sacred import Experiment
from sacred.utils import apply_backspaces_and_linefeeds
from torch.autograd import Variable
import yaml
yaml.warnings({'YAMLLoadWarning': False})

import lbforaging
import Wolfpack_gym

import utils
# Own imports
from envs import make_env
from storage import RolloutStorage

# Create Sacred Experiment
ex = Experiment("POMRL")
ex.captured_out_filter = apply_backspaces_and_linefeeds
# np.seterr(all='raise')

# Get name of environment yaml file.
# Should be specified in command line using
# 'python main.py with environment.config_file=name_of_env_config_file.yaml'
environment_yaml = utils.get_environment_yaml(ex)

# Add defautl.yaml and the <environment_name>.yaml file to the sacred configuration
DIR = os.path.dirname(sys.argv[0])
DIR = "." if DIR == "" else DIR
ex.add_config(DIR + "/conf/default.yaml")
ex.add_config(DIR + "/conf/" + environment_yaml)

from sacred.observers import FileStorageObserver

ex.observers.append(FileStorageObserver.create("test_runs"))


from gym.envs.registration import register

death_valley_configs = {
    "transition_std": 0.025,
    "observation_std": 0.0,
    "goal_reward": None,
    "goal_position": [0.7, 0.5],
    "goal_radius": 0.1,
    "goal_end": False,
    "outside_box_cost": -1.5,
    "starting_position": [-0.85, -0.85],
    "starting_std": 0.1,
    "max_time": 100,
    "max_action_value": 0.05,
    "action_cost_factor": 0.1,
    "shaping_power": 4,
    "hill_height": 4,
    "box_scale": 10,
}
register(
    id="DeathValley-v0",
    entry_point="environments.death_valley:DeathValleyEnv",
    kwargs=death_valley_configs,
    max_episode_steps=75,
)


# This function is called by sacred before the experiment is started
# All args are provided by sacred and filled with configuration values
@ex.config
def general_config(cuda, algorithm, environment, rl_setting, loss_function, log):
    """
    - Sets device=cuda or, if cuda is 'auto' sets it depending on availability of cuda
    - Entries in algorithm.model are overriden with new values from environment.model_adaptation
    - Entries in rl_setting are overriden with new values from environment.rl_setting_adaptation
    - algorithm.model.batch_size is set to rl_setting.num_processes
    """

    if cuda == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = cuda

    # This updates values in environment.model based on values in environment.model_adaption
    # This allows environment specific model configuration to be specified in the environment.yaml
    for key1 in environment["model_adaptation"]:
        algorithm["model"][key1] = environment["model_adaptation"][key1]

    # Same for values in rl_setting
    for key2 in environment["rl_setting_adaptation"]:
        rl_setting[key2] = environment["rl_setting_adaptation"][key2]

    # Delete keys so we don't have them in the sacred configuration
    del key1
    del key2

    algorithm["model"]["batch_size"] = rl_setting["num_processes"]

    if loss_function["encoding_loss_coef"] == 0:
        algorithm["model"]["resample"] = False

    from sys import platform

    if platform == "darwin":
        # rl_setting['num_processes'] = 2
        if environment["config_file"] == "openaiEnv.yaml":
            # Workaround for bug in openCV on MacOS
            # Problem araises in WarpFrame wrapper in cv2
            # See here: https://github.com/opencv/opencv/issues/5150
            multiprocessing.set_start_method("spawn")


@ex.command(unobserved=True)
def setup(rl_setting, device, _run, _log, log, seed, cuda):
    """
    Do everything required to set up the experiment:
    - Create working dir
    - Set's cuda seed (numpy is set by sacred)
    - Set and configure logger
    - Create n_e environments
    - Create model
    - Create 'RolloutStorage': A helper class to save rewards and compute the advantage loss
    - Creates and initialises current_memory, a dictionary of (for each of the n_e environment):
      - past observation
      - past latent state
      - past action
      - past reward
      This is used as input to the model to compute the next action.

    Warning: It is assumed that visual environments have pixel values [0,255].

    Args:
        All args are automatically provided by sacred by passing the equally named configuration
        variables that are either defined in the yaml files or the command line.

    Returns:
        id_temp_dir (str): The newly created working directory
        envs: Vector of environments
        actor_critic: The model
        rollouts: A helper class (RolloutStorage) to store rewards and compute TD errors
        current_memory: Dictionary to keep track of current obs, actions, latent states and rewards
    """

    # Create working dir
    id_tmp_dir = "{}/{}/".format(log["tmp_dir"], _run._id)
    print(id_tmp_dir, _run._id)

    utils.safe_make_dirs(id_tmp_dir)

    np.set_printoptions(precision=2)

    torch.manual_seed(seed)
    if cuda:
        torch.cuda.manual_seed(seed)

    # Forgot why I need this?
    # os.environ['OMP_NUM_THREADS'] = '1'

    logger = logging.getLogger()
    if _run.debug or _run.pdb:
        logger.setLevel(logging.DEBUG)

    envs = register_and_create_Envs(id_tmp_dir)
    actor_critic = create_model(envs)

    obs_shape = envs.observation_space.shape
    obs_shape = (obs_shape[0], *obs_shape[1:])

    rollouts = RolloutStorage(
        rl_setting["num_steps"],
        rl_setting["num_processes"],
        obs_shape,
        envs.action_space,
    )
    current_obs = torch.zeros(rl_setting["num_processes"], *obs_shape)

    obs = envs.reset()
    if not actor_critic.observation_type == "fc":
        obs = obs / 255.0
    # print(obs)
    current_obs = torch.from_numpy(obs).float()
    # init_states = Variable(torch.zeros(rl_setting['num_processes'], actor_critic.state_size))
    init_states = actor_critic.new_latent_state()
    init_rewards = torch.zeros([rl_setting["num_processes"], 1])

    if envs.action_space.__class__.__name__ == "Discrete":
        action_shape = 1
    else:
        action_shape = envs.action_space.shape[0]
    init_actions = torch.zeros(rl_setting["num_processes"], action_shape)

    init_states = init_states.to(device)
    init_actions = init_actions.to(device)
    current_obs = current_obs.to(device)
    init_rewards = init_rewards.to(device)
    actor_critic.to(device)
    rollouts.to(device)

    current_memory = {
        "current_obs": current_obs,
        "states": init_states,
        "oneHotActions": utils.toOneHot(envs.action_space, init_actions),
        "rewards": init_rewards,
    }

    return id_tmp_dir, envs, actor_critic, rollouts, current_memory


@ex.command
def create_model(envs, algorithm, rl_setting):
    """
    Creates the actor-critic model.
    If algorithm.use_particle_filter == True use DVRL
    else use RNN

    Configuration for RNN is in algorithm.model
    Configuration for DVRL is in algorithm.model AND algorithm.particle_filter

    Note that those values can be overwritten by the environment (see config() function).

    Args:
        envs: Vector of environments. Usually created by register_and_create_Envs()
        All other args are automatically provided by sacred by passing the equally named
        configuration variables that are either defined in the yaml files or the command line.

    Returns:
        model: The actor_critic model
    """
    action_space = envs.action_space
    nr_inputs = envs.observation_space.shape[0]

    if algorithm["use_particle_filter"]:
        from pf_model import DVRLPolicy

        # Pass in configuration from algorithm.model AND algorithm.particle_filter
        model_params = algorithm["model"]
        model_params.update(algorithm["particle_filter"])
        model = DVRLPolicy(action_space, nr_inputs, **model_params)
    else:
        from model import RNNPolicy

        # Pass in configuration only from algorithm.model
        model = RNNPolicy(action_space, nr_inputs, **algorithm["model"])
    return model


@ex.capture
def register_and_create_Envs(id_tmp_dir, seed, environment, rl_setting):
    """
    Register environment, create vector of n_e environments and return it.

    Args:
        id_temp_dir (str): Working directory.
        All other args are automatically provided by sacred by passing the equally named
        configuration variables that are either defined in the yaml files or the command line.

    """
    if environment["entry_point"]:
        try:
            register(
                id=environment["name"],
                entry_point=environment["entry_point"],
                kwargs=environment["config"],
                max_episode_steps=environment["max_episode_steps"],
            )
        except Exception:
            pass

    envs = [
        make_env(
            environment["name"],
            100 * i + seed,
            i,
            None,
            frameskips_cases=environment["frameskips_cases"],
        )
        for i in range(rl_setting["num_processes"])
    ]

    print("env seed",  seed)
    # Vectorise envs
    if rl_setting["num_processes"] > 1:
        envs = SubprocVecEnv(envs)
    else:
        envs = DummyVecEnv(envs)

    # Normalise rewards. Unnecessary for Atari, unwanted for Mountain Hike.
    # Probably useful for MuJoCo?
    # if len(envs.observation_space.shape) == 1:
    if environment["vec_norm"]:
        envs = VecNormalize(envs)

    return envs


@ex.capture
def run_model(
    actor_critic,
    current_memory,
    envs,
    environment,
    rl_setting,
    device,
    predicted_times=None,
    deterministic=True
):
    """
    Runs the model.

    Args:
        actor_critic: Agent model
        current_memory: Dict with past observations, actions, latent_states and rewards
        envs: Vector of n_e environments
        All other args are automatically provided by sacred by passing the equally named
        configuration variables that are either defined in the yaml files or the command line.

    Returns:
        policy_return: Named tuple with, besides other values, new latent state, V, a, log p(a),
                       H[p(a)], encding loss L^{ELBO}
    """

    # Run model
    policy_return = actor_critic(
        current_memory=current_memory,
        predicted_times=predicted_times,
        deterministic=True
    )

    # Execute on environment
    cpu_actions = policy_return.action.detach().squeeze(1).cpu().numpy()
    #print("a", cpu_actions)
    obs, reward, done, info = envs.step(cpu_actions)
    # envs.render()
    #print("r", reward)
    if not actor_critic.observation_type == "fc":
        obs = obs / 255.0

    # Flickering: With probability p_blank, set observation to 0
    blank_mask = np.random.choice(
        [0, 1],
        size=rl_setting["num_processes"],
        p=[environment["p_blank"], 1 - environment["p_blank"]],
    )
    obs_dims = [1] * len(envs.observation_space.shape)
    blank_mask = np.reshape(blank_mask, (rl_setting["num_processes"], *obs_dims))
    obs = obs * blank_mask

    # Make reward into tensor so we can use it as input to model
    reward_tensor = torch.from_numpy(np.expand_dims(np.stack(reward), 1)).float()
    
    # If trajectory ended, create mask to clean reset actions and latent states
    masks = torch.FloatTensor([[0.0] if done_ else [1.0] for done_ in done])
    masks = masks.to(device)

    # Update current_memory
    current_memory["current_obs"] = torch.from_numpy(obs).float()

    # Create new latent states for new episodes
    current_memory["states"] = actor_critic.vec_conditional_new_latent_state(
        policy_return.latent_state, masks
    )

    # Set first action to 0 for new episodes
    # Also, if action is discrete, convert it to one-hot vector
    current_memory["oneHotActions"] = utils.toOneHot(
        envs.action_space,
        policy_return.action * masks.type(policy_return.action.type()),
    )

    current_memory["rewards"][:] = reward_tensor

    return policy_return, current_memory, blank_mask, masks, reward, done 


@ex.capture
def track_values(tracked_values, policy_return):
    """
    Save various values from policy_return into 'tracked_values', a dictionary of lists (or deques).

    Args:
        tracked_values: Dictionary of list-like objects.
        policy_return: Named tuple returned by actor_critic model
        old_observation
    """

    tracked_values["values"].append(policy_return.value_estimate)
    tracked_values["action_log_probs"].append(policy_return.action_log_probs)
    tracked_values["dist_entropy"].append(policy_return.dist_entropy)
    tracked_values["num_killed_particles"].append(policy_return.num_killed_particles)

    # For loss function
    tracked_values["encoding_loss"].append(policy_return.total_encoding_loss)

    # For Metrics
    tracked_values["prior_loss"].append(policy_return.encoding_losses[0])
    tracked_values["emission_loss"].append(policy_return.encoding_losses[1])
    return tracked_values


@ex.capture
def save_images(policy_return, old_observation, id_tmp_dir, j, step, _run, log):
    """
    Save images predicted by model to database.
    Args:
        policy_return: NamedTuple returned by actor critic. Contains:
            - predicted_obs_img: Averaged prediction
            - particle_obs_img: Predictions for each particle
        old_observation: Ground truth observation at current time
        id_tmp_dir: Working directory
        j: Current gradient update step
        step: Current step of the n_s steps of n-step A2C
        _run, log: Provided by sacred
    """

    for dt, img, p_img in zip(
        log["predicted_times"],
        policy_return.predicted_obs_img,
        policy_return.particle_obs_img,
    ):
        utils.save_numpy(
            dir=id_tmp_dir,
            name="update{}_step{}_dt{}.npy".format(j, step, dt),
            array=img.detach().cpu().numpy(),
            _run=_run,
        )

        if log["save_particle_reconstruction"]:
            utils.save_numpy(
                dir=id_tmp_dir,
                name="update{}_step{}_dt{}_particles.npy".format(j, step, dt),
                array=p_img.detach().cpu().numpy(),
                _run=_run,
            )

    utils.save_numpy(
        dir=id_tmp_dir,
        name="update{}_step{}_obs.npy".format(j, step, dt),
        array=old_observation.cpu().numpy(),
        _run=_run,
    )


@ex.capture
def track_rewards(tracked_rewards, reward, masks, blank_mask, rl_setting):
    masks = masks.cpu()
    # Initialise first time

    # Track episode and final rewards as well as how many episodes have ended so var
    tracked_rewards["episode_rewards"] += reward
    tracked_rewards["num_ended_episodes"] += rl_setting["num_processes"] - sum(masks)[0]
    tracked_rewards["final_rewards"] *= masks
    tracked_rewards["final_rewards"] += (1 - masks) * tracked_rewards["episode_rewards"]
    tracked_rewards["episode_rewards"] *= masks
    tracked_rewards["nr_observed_screens"].append(float(sum(blank_mask)))

    avg_nr_observed = (
        sum(list(tracked_rewards["nr_observed_screens"])[0 : rl_setting["num_steps"]])
        / rl_setting["num_steps"]
        / rl_setting["num_processes"]
    )

    return (
        tracked_rewards["final_rewards"],
        avg_nr_observed,
        tracked_rewards["num_ended_episodes"],
    )


@ex.automain
def main(_run, seed, opt, environment, rl_setting, log, algorithm, loss_function, load, device):
    """
    Entry point. Contains main training loop.
    """


    # Setup directory, vector of environments, actor_critic model, a 'rollouts' helper class
    # to compute target values and 'current_memory' which maintains the last action/observation/latent_state values
    id_tmp_dir, envs, actor_critic, rollouts, current_memory = setup()

    tracked_rewards = {
        # Used to tracked how many screens weren't blanked out. Usually not needed
        "nr_observed_screens": collections.deque(
            [0], maxlen=rl_setting["num_steps"] + 1
        ),
        "episode_rewards": torch.zeros([rl_setting["num_processes"], 1]),
        "final_rewards": torch.zeros([rl_setting["num_processes"], 1]),
        "num_ended_episodes": 0,
    }

    num_updates = int(
        float(loss_function["num_frames"])
        // rl_setting["num_steps"]
        // rl_setting["num_processes"]
    )

    # Count parameters
    num_parameters = 0
    for p in actor_critic.parameters():
        num_parameters += p.nelement()

    # Initialise optimiser
    if opt["optimizer"] == "RMSProp":
        optimizer = optim.RMSprop(
            actor_critic.parameters(), opt["lr"], eps=opt["eps"], alpha=opt["alpha"]
        )
    elif opt["optimizer"] == "Adam":
        optimizer = optim.Adam(
            actor_critic.parameters(), opt["lr"], eps=opt["eps"], betas=opt["betas"]
        )

    obs_loss_coef = (
        algorithm["particle_filter"]["obs_loss_coef"]
        if algorithm["use_particle_filter"]
        else algorithm["model"]["obs_loss_coef"]
    )

    print(actor_critic)
    logging.info("Number of parameters =\t{}".format(num_parameters))
    logging.info("Total number of updates: {}".format(num_updates))
    logging.info("Learning rate: {}".format(opt["lr"]))
    utils.print_header()

    # utils.load_model(id_tmp_dir, name, load["epoch"], actor_critic, _run)
    # actor_critic = utils.load_model(load["run"], "model_epoch_{}".format(load["epoch"]),  actor_critic, _run)
    #utils.save_model(id_tmp_dir, "model_epoch_{}".format(j), actor_critic, _run)
    
    start = time.time()
    number_of_epochs = 40
    max_number_of_epochs = 40
    avgs_reward_per_epoch = []
    epoch_count = []
    # Main training loop
    for epoch in range(number_of_epochs):
        

        # for j in range(1):
        epoch_count.append(epoch)
        if epoch==max_number_of_epochs:
            actor_critic = utils.load_model(log["test_dir"], load["run"], "model_final",  actor_critic, _run)
        else:    
            actor_critic = utils.load_model(log["test_dir"], load["run"], "model_epoch_{}".format(epoch*2000),  actor_critic, _run)

        envs = register_and_create_Envs(id_tmp_dir)
 
        obs_shape = envs.observation_space.shape
        obs_shape = (obs_shape[0], *obs_shape[1:])

        rollouts = RolloutStorage(
            rl_setting["num_steps"],
            rl_setting["num_processes"],
            obs_shape,
            envs.action_space,
        )
        current_obs = torch.zeros(rl_setting["num_processes"], *obs_shape)

        obs = envs.reset()
        if not actor_critic.observation_type == "fc":
            obs = obs / 255.0
        # print(obs)
        current_obs = torch.from_numpy(obs).float()
        # init_states = Variable(torch.zeros(rl_setting['num_processes'], actor_critic.state_size))
        init_states = actor_critic.new_latent_state()
        init_rewards = torch.zeros([rl_setting["num_processes"], 1])

        if envs.action_space.__class__.__name__ == "Discrete":
            action_shape = 1
        else:
            action_shape = envs.action_space.shape[0]
        init_actions = torch.zeros(rl_setting["num_processes"], action_shape)

        init_states = init_states.to(device)
        init_actions = init_actions.to(device)
        current_obs = current_obs.to(device)
        init_rewards = init_rewards.to(device)
        actor_critic.to(device)
        rollouts.to(device)

        current_memory = {
            "current_obs": current_obs,
            "states": init_states,
            "oneHotActions": utils.toOneHot(envs.action_space, init_actions),
            "rewards": init_rewards,
        }

        # Only predict observations sometimes: When predicted_times is a list of ints,
        # predict corresponding future observations, with 0 being the current reconstruction
        # if (
        #     log["save_reconstruction_interval"] > 0
        #     and float(obs_loss_coef) != 0
        #     and (j % log["save_reconstruction_interval"] == 0 or j == num_updates - 1)
        # ):
        #     predicted_times = log["predicted_times"]
        # else:
        #     predicted_times = None

        #predicted_times = log["predicted_times"] ########################################## 
        predicted_times = None
        # Main Loop over n_s steps for one gradient update
        
        num_dones = [0] * rl_setting["num_processes"]
        per_worker_rew = [0.0] * rl_setting["num_processes"]
        avgs = []
        step = 0 
        num_eval_episodes = 3 
        while (any([k < num_eval_episodes for k in num_dones])):
        # for i in range(60):
            print(step)
            old_observation = current_memory["current_obs"]

            policy_return, current_memory, blank_mask, masks, reward, dones, = run_model(
                actor_critic=actor_critic,
                current_memory=current_memory,
                envs=envs,
                predicted_times=predicted_times,
                deterministic=True
            )
            # input()
            #print(dones)
            per_worker_rew = [k + l for k, l in zip(per_worker_rew, reward)]
            # print(per_worker_rew)
            for idx, flag in enumerate(dones):
                if flag:
                    if num_dones[idx] < num_eval_episodes:
                        num_dones[idx] += 1
                        avgs.append(per_worker_rew[idx])
                    per_worker_rew[idx] = 0

            #print("per_worker_rew", per_worker_rew)
            #print("num_dones", num_dones)
            step +=1

        avg_total_rewards = (sum(avgs) + 0.0) / len(avgs)
        avgs_reward_per_epoch.append(avg_total_rewards)
        print("Finished train with rewards " + str(avg_total_rewards))
        envs.close()
        
    import pandas as pd
  
    # initialize list elements
    # step = np.linspace(0,number_of_epochs, num=number_of_epochs, dtype=np.int16)
    data = {"step": epoch_count, "train_loss":avgs_reward_per_epoch}  
    # Create the pandas DataFrame with column name is provided explicitly
    df = pd.DataFrame(data) # avgs_reward_per_epoch, columns=['Numbers'])
      
    # print dataframe.
    print(df)
    if environment["train"]:
        data_type = "train"
        file_name = "TRAIN"
    else: 
        data_type = "train"
        file_name = "TEST"
    # long name 
    # directory = log["test_dir"]+ '/' + str(load["run"])  + '/' + data_type + '_data_' + str(load["run"]) + '.csv'
    # short name
    directory = log["test_dir"]+ '/' + str(load["run"])  + '/' + file_name + '.csv'
    print(directory)
    df.to_csv(directory, index=False)
    
    print(avg_total_rewards)
    print("Finished training")
