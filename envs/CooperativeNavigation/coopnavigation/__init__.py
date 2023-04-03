from gym.envs.registration import registry, register, make, spec
from itertools import product

sights = range(1,13)
sizes = range(5, 13)

for s in sizes:
    register(
        id="MARL-Navigation-{0}x{0}-v0".format(s),
        entry_point="coopnavigation.navigation:MARLNavigationEnv",
        kwargs={
            "players": 5,
            "field_size": (s, s),
            "sight": s,
            "max_episode_steps": 50,
            "seed": 100,
            "effective_max_num_players": 3,
            "init_num_players": 3,
            "with_shuffle": True,
            "gnn_input": False,
            "with_openness": True,
            "with_gnn_shuffle": False,
            "collapsed": False
        },
    )

for sight, s in product(sights, sizes):
    register(
        id="PO-Navigation-{0}-{1}x{1}-v0".format(sight, s),
        entry_point="coopnavigation.navigation:NavigationEnv",
        kwargs={
            "players": 5,
            "field_size": (s, s),
            "sight": sight,
            "other_player_sight": s,
            "max_episode_steps": 50,
            "seed": 100,
            "effective_max_num_players": 3,
            "init_num_players": 3,
            "with_shuffle": True,
            "gnn_input": False,
            "with_openness": True,
            "with_gnn_shuffle": False,
            "collapsed": False,
            "designated_device": "cuda:0"
        },
    )

for sight, s in product(sights, sizes):
    register(
        id="PO-Navigation-{0}-{1}x{1}-v1".format(sight, s),
        entry_point="coopnavigation.navigation:NavigationEnvV2",
        kwargs={
            "players": 5,
            "field_size": (s, s),
            "sight": sight,
            "other_player_sight": s,
            "max_episode_steps": 50,
            "seed": 100,
            "effective_max_num_players": 3,
            "init_num_players": 3,
            "with_shuffle": False,
            "gnn_input": False,
            "with_openness": True,
            "with_gnn_shuffle": False,
            "collapsed": False,
            "designated_device": "cpu",
            "disappearance_prob": 0.,
            "perturbation_prob": [1.,0.,0.]
        },
    )


for sight, s in product(sights, sizes):
    register(
        id="PO-Navigation-DVRL-{0}-{1}x{1}-v1".format(sight, s),
        entry_point="coopnavigation.navigation:NavigationEnvV2",
        kwargs={
            "players": 5,
            "field_size": (s, s),
            "sight": sight,
            "other_player_sight": s,
            "max_episode_steps": 50,
            "seed": 100,
            "effective_max_num_players": 3,
            "init_num_players": 3,
            "with_shuffle": False,
            "gnn_input": True,
            "with_openness": True,
            "with_gnn_shuffle": True,
            "collapsed": False,
            "designated_device": "cpu",
            "disappearance_prob": 0.,
            "perturbation_prob": [1.,0.,0.],
            'ready_obs': True
        },
    )

for sight, s in product(sights, sizes):
    register(
        id="PO-Navigation-DVRL-t-{0}-{1}x{1}-v1".format(sight, s),
        entry_point="coopnavigation.navigation:NavigationEnvV2",
        kwargs={
            "players": 5,
            "field_size": (s, s),
            "sight": sight,
            "other_player_sight": s,
            "max_episode_steps": 50,
            "seed": 100,
            "effective_max_num_players": 5,
            "init_num_players": 5,
            "with_shuffle": False,
            "gnn_input": True,
            "with_openness": True,
            "with_gnn_shuffle": True,
            "collapsed": False,
            "designated_device": "cpu",
            "disappearance_prob": 0.,
            "perturbation_prob": [1.,0.,0.],
            'ready_obs': True
        },
    )