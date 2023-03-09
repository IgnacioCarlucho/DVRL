import gym

import Wolfpack_gym
env = gym.make('Adhoc-DVRL-wolfpack-v5')

SAMPLE = True

print(env.observation_space)
#for j in range(7):
obs = env.reset()
print(obs)
env.render()
for _ in range(50):
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
    #imageio.imwrite('filename.jpg', img)
    state, r , done , _  = env.step(action) # take a random action
    print(state, r , done)
    # print(state,  r , done )
    env.render()






