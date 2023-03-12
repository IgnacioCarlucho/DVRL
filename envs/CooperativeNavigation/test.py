import gym
import coopnavigation

import lbforaging
env = gym.make('PO-Navigation-DVRL-2-12x12-v1')
# env = gym.make('PO-Adhoc-DVRL-Foraging-2-12x12-3f-v0')


SAMPLE = True

print(env.observation_space)
#for j in range(7):
obs = env.reset()
print(obs)
action_space = env.action_space
nr_inputs = env.observation_space

print(action_space)
print(nr_inputs)
print(nr_inputs.shape)


for j in range(5):
    obs = env.reset()
    for _ in range(10):
        # img = env.render()
        # print(env.action_space.sample())
        if SAMPLE:
            action = env.action_space.sample()
        else: 
            key = input("a,w,s,d,f: ")
            print(key)
            if key=="a":
                action = 3
            elif key=="w":
                action = 1
            elif key=="s":
                action = 2
            elif key=="d":
                action = 4
            elif key=="f":
                action = 0

        print("a", action)
        state, r , done , _  = env.step(action) # take a random action
        print(state, r , done)
        # print(state,  r , done )
       





