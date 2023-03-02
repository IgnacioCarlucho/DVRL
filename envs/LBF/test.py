import gym

import lbforaging
env = gym.make('PO-Adhoc-DVRL-Foraging-2-15x15-3f-v0')



print(env.observation_space)
#for j in range(7):
env.reset()
for _ in range(10):
    # img = env.render()
    # print(env.action_space.sample())

    #imageio.imwrite('filename.jpg', img)
    state, r , done , _  = env.step(1) # take a random action
    print(state, _)
    # print(state,  r , done )
    env.render()
    input()





