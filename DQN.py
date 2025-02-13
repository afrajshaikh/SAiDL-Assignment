# -*- coding: utf-8 -*-
"""improved.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1IKNWWaImAKsKtKCaKfNl7Sb7uEXXIi21
"""

from google.colab import drive 
drive.mount('/content/gdrive')

lr = 0.01
capacity = 50000                    #Storage capacity.
epsilon = 0.01
batch_size = 64
gamma = 0.9
reward_list = []                    #For appending rewards.

import random

import numpy as np
import pandas as pd
import torch
import torch.nn as nn 
import torch.nn.functional as F
from collections import namedtuple
import matplotlib.pyplot as plt


class GameManager:
    """
    This is the GameManager class which will act as the environment for the
    assignment.

    Some features:
        There are 2 folders: stats, moves. These contain some common pokemon
            data and moves data. You can refer to these or even add to them if
            you want to. (do note down all changes you make and mention them
            in the answer doc)
        There is the type chart. The type chart is a damage multiplier chat.
        There is a separate file to hold the Opponent class but it isn't nec
    """

    def __init__(self, stats=None, moves=None, poke_per_team=3):
        # Get the database of all pokemon (their names, types,
        # hps and available moves)
        self.stats = (
            pd.read_csv(r"/content/gdrive/My Drive/RL PokeBattle/pokebattle/data/stats.csv")
            if stats is None
            else pd.read_csv("{}".format(stats))
        )
        # # Get the database of moves
        self.moves_dict = (
            pd.read_csv(r"/content/gdrive/My Drive/RL PokeBattle/pokebattle/data/moves.csv")
            if moves is None
            else pd.read_csv("{}".format(moves))
        )

        self.moves = self.moves_dict.copy()
        # Row corresponds to attacker, column corresponds to defender
        # Read up on how this works if you're interested
        self.type_chart = np.array(
            [
                [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
                [1.0, 0.5, 0.5, 1.0, 2.0, 2.0],
                [1.0, 2.0, 0.5, 1.0, 0.5, 1.0],
                [1.0, 1.0, 2.0, 0.5, 0.5, 1.0],
                [1.0, 0.5, 2.0, 1.0, 0.5, 1.0],
                [1.0, 0.5, 0.5, 1.0, 2.0, 0.5],
            ]
        )
        # Define some common lists for printing and debugging purposes
        self.types = ["Normal", "Fire", "Water", "Electric", "Grass", "Ice"]
        self.poke_list = list(self.stats["pokemon"])
        self.moves_list = list(self.moves["move"])

        # Replace the columns with numbers
        self.moves["move"] = range(len(self.moves))
        self.moves["type"] = pd.Series(
            [self.types.index(i) for i in self.moves["type"]]
        )
        self.moves = self.moves.to_numpy()

        # Replace string pokemon names with their respective numerical indices
        self.stats["pokemon"] = self.stats.index
        self.stats["type"] = pd.Series(
            [self.types.index(i) for i in self.stats["type"]]
        )
        for i in range(4):
            key = "move" + str(i + 1)
            self.stats[key] = pd.Series(
                [self.moves_list.index(j) for j in self.stats[key]]
            )

        # Number of pokemon per team
        self.poke_per_team = poke_per_team

        # Initialise both teams
        self.team = self._init_team()
        self.opp_team = self._init_team()

        # Initialise the starting pokemon of each team
        self.index = random.randint(0, self.poke_per_team - 1)
        self.opp_index = random.randint(0, self.poke_per_team - 1)

        # True if it's the player's turn, False if it's the opponent's turn
        # By default, the player plays first with 50% probability
        self.turn = True if np.random.uniform() < 0.5 else False

    @property
    def action_space(self):
        """
        Defines the action space of the game. It will be the indices of all the
        values in num of moves + 2 extra actions to allow switching of pokemon
        """
        return tuple(range(6))

    def _init_team(self):
        """
        Helper function to initialise the teams
        """
        indices = random.sample(range(len(self.stats)), self.poke_per_team)
        team = np.array([self.stats.iloc[index] for index in indices]).astype(int)
        return team

    def reset(self):
        """
        Performs env.reset() like in Gym Environments
        """
        self.index = random.randint(0, self.poke_per_team - 1)
        self.opp_index = random.randint(0, self.poke_per_team - 1)
        self.turn = True if np.random.uniform() < 0.5 else False

        self.team, self.opp_team = self._init_team(), self._init_team()

        # It's upto you what you define the state space to be.
        # This is an example (not a very good one)
        state = np.array([self.team, self.opp_team])
        return state

    def validate_hp(self, player=True):
        """
        Validates the HP. You can add other validation checks here.

        Args:
            player (bool): True if the Player's HP needs to be checked
        """
        if player:
            hp = self.team[self.index][2]
        else:
            hp = self.opp_team[self.opp_index][2]
        return hp > 0

    def opp_step(self):
        """
        Performs env.step() like in Gym Environments for the Opponent AI
        """
        # The Opponent AI here basically picks the move with the highest damage
        # It won't switch until it's out of HP
        actions = self.opp_team[self.opp_index][3:]
        damages = np.array([self.moves[i][2] for i in actions])
        action = np.argmax(damages)
        # print(action)               #int
        assert self.index in range(3) and self.opp_index in range(
            3
        ), "Index: {}, Opp Index: {}".format(self.index, self.opp_index)

        if action == len(self.moves):  # Switches to the pokemon to the right
            self.opp_index = (
                self.opp_index + 1 if self.opp_index < self.poke_per_team else 0
            )
            self.damage = 0
        elif action == len(self.moves) + 1:  # Switches to the pokemon to the left
            self.opp_index = (
                self.opp_index - 1 if self.opp_index > 0 else self.poke_per_team - 1
            )
            self.damage = 0
        else:
            # A proper move is performed and the damage inflicted
            # needs to be calculated
            _, move_type, power, _, acc = self.moves[action]
            type_factor = self.type_chart[self.opp_team[self.opp_index][1]][
                int(move_type)
            ]
            self.damage = power * acc * type_factor
            self.team[self.index][2] -= self.damage

        for _ in range(3):
            if self.validate_hp():
                break
            # By default, if the current Pokemon is out of HP, the pokemon
            # to the right is chosen
            self.index = self.index + 1 if self.index < self.poke_per_team - 1 else 0
        

    def step(self, action):
        """
        Performs env.step() like in Gym Environments for the Agent

        Args:
            action (np.ndarray): Action to be taken
                0, 1, 2, 3: Moves of the pokemon
                4: Switch to the pokemon on the left (if there's no pokemon on
                    the left, it'll switch to the pokemon on the extreme right)
                5: Switch to the pokemon on the right (opposite of the above
                    in the extreme case)
        """
        if not self.turn:
            self.opp_step()

        if action == 4:  # Switches to the pokemon to the right
            self.index = self.index + 1 if self.index < self.poke_per_team - 1 else 0
            self.damage = 0
            type_factor = 1
        elif action == 5:  # Switches to the pokemon to the left
            self.index = self.index - 1 if self.index > 0 else self.poke_per_team - 1
            self.damage = 0
            type_factor = 1
        else:
            # A proper move is performed and the damage inflicted
            # needs to be calculated
            move = self.team[self.index][3 + action]
            _, move_type, power, _, acc = self.moves[move]
            assert self.index in range(3) and self.opp_index in range(3)
            type_factor = self.type_chart[self.team[self.index][1]][int(move_type)]
            self.damage = power * acc * type_factor
            self.opp_team[self.opp_index][2] -= self.damage

        self.turn = not self.turn

        # The following is again just example code. All this can be modified.
        # Document all the changes you're making
        """
        For reward, I have not made any changes in this code. I was thinking of
        keeping +10 reward when opponent's hp finishes and -10 when agent's hp 
        finishes. But since opp_step is coded in such a way that opponent takes step 
        till it run out of its hp so I decided to keep it same. 
        """
        reward = self.damage / 100
        next_state = np.array([self.team, self.opp_team])

        # This defines the game over status. In this case, this is simply set
        # to True if the current pokemon's HP goes less than 0
        for _ in range(3):
            if self.validate_hp(False):
                done = False
                break
            self.opp_index = (
                self.opp_index + 1 if self.opp_index < self.poke_per_team - 1 else 0
            )
        else:
            done = True

        info = {}  # Can be used to store any additional variables for training

        return next_state, reward, done, info

game = GameManager(None , None)                 # Instantiating GameManager() class.



"""
The remaining code block is taken from Agent.py file. I have written docstrings wherever I have edited or written the code. 
"""
import numpy as np

"""
My agent will use Deep Q-Network for selecting actions in this enviornment. 
The main aim of selecing this network is to predict the action-value function
correctly. In this case state is very complex so neural networks will act as a
good function approximator.

My input feature is taking rows of those pokemon who are playing the match from
the state. Instead of using make_model function I used Neural_Net class.  
"""


# This class is our neural network.

class Neural_Net(nn.Module):
    def __init__(self):
      # self.Manager = GameManager()
      # self.state = state
      super().__init__()
      self.net = nn.Sequential(
          nn.Linear(14 ,20),
          nn.ReLU(),

          nn.Linear(20, 10),
          nn.ReLU(),

          nn.Linear(10,6)
      )

    def forward(self, x):
        return self.net(x)
    
    
"""
This class converts state into suitable tensor so that it could be taken as an 
input in the Neural_Net class.
"""
class state_processing():
    def __init__(self, state):
        self.state = state
        self.manager = game

    def state_process(self):
        initial = self.state
        input_list = initial[0][self.manager.index].tolist() + initial[1][self.manager.opp_index].tolist()
        input_array = np.asarray(input_list)
        return torch.FloatTensor(input_array).unsqueeze(0)


# Transition will act as a tuple for storing memory.
Transition = namedtuple('Transition',('state', 'action','next_state','reward','done')) 

"""
ReplayMemory() class is used to stored and sampling memory for training DQN 
through experienced replay.
"""
class ReplayMemory():

    def __init__(self,capacity, batch_size):
        self.capacity = capacity
        self.memory = []
        self.index_counter =0
        self.batch_size = batch_size

    def push(self,Transition):                      #Appends experience.
      if len(self.memory) < self.capacity:
        self.memory.append(Transition)
      else:
        self.memory[self.index_counter % self.capacity] = Transition

    def sample(self):                               # For sampling experience.
      if len(self.memory) >= self.batch_size:
        experience = random.sample(self.memory, self.batch_size)
        return experience

    



class Agent:
    def __init__(self, game, DQN = Neural_Net()):
        self.game = game
        self.team = game.team
        self.opponent = game.opp_team
        self.train_net = DQN                    # Training network
        self.target_net = DQN                   # Target network
        self.state = self.game.reset()
        self.replay_memory = ReplayMemory(capacity,batch_size)
        self.processing = state_processing(self.state)

        # The array of all the agents moves
        self.moves = np.array(
            [
                [self.game.moves[self.team[i][j + 3]] for j in range(4)]
                for i in range(len(self.team))
            ]
        )

        # The index of the current pokemon is maintained by the GameManager
        self.current_pokemon = self.team[self.game.index]


    def select_action(self, state):
        """
        Our agent follows e-greedy strategy for selecting actions in the enviornment. 
        """

        if np.random.random() < epsilon:
          return np.random.randint(0,6)
        else:
          with torch.no_grad():
            input_array = self.processing.state_process()        
            return self.train_net(input_array).max(1)[1].item()



        # Example code, replace this with your logic:
        # Returns move which inflicts maximum damage


        # action = self.moves[self.game.index].T[1].argmax()
        # return action

    def update(self):
        """
        Use this to update your model (whether it be a table, policy,
        actor-critic network, Q-value etc)
        """


        # Making separate batches(tuple) of state, reward, next_satate, done, action. 
        batch = Transition(*zip(*self.replay_memory.sample()))


        # Here we are basically converting them into tensors as our neural 
        # network would be taking tensors as input.

        action_tensor = torch.LongTensor(batch.action).reshape((1, -1))
        reward_tensor = torch.Tensor(batch.reward).unsqueeze(1)
        done_tensor = torch.Tensor(batch.done).unsqueeze(1)
        state_tensor = self.processing.state_process()     
        next_state_tensor = self.processing.state_process()
        
        # Getting q_values from training neural network.
        current_q_values =  self.train_net(state_tensor).gather(1, action_tensor)

        # Getting next state q_values from target neural network.
        next_q_values = self.target_net(next_state_tensor).max(1)[0].view(-1,1)

        expected_q_values = reward_tensor + gamma*(next_q_values)
        
        criterion = nn.MSELoss()
        loss = criterion(current_q_values, expected_q_values)
        optimizer = torch.optim.SGD(self.train_net.parameters(), lr = lr)
        optimizer.zero_grad()

        loss.backward()
        optimizer.step()

        
        # pass

    def learn(self, num_epochs=10, episode_len=10):
        """
        This function can be used for the actual training loops. You can keep
        it here or have an external class for training loops.

        Args:
            num_epochs (int): Number of epochs to train the agent for
            episode_len (int): Number of timesteps (not including
                opponent timesteps) per pokebattle
        """
        # Example code given below

        self.update_weights =200              # Decides when to update weights.

        for epoch in range(num_epochs):
            state = self.state 
            episode_reward = 0



            


            for timestep in range(episode_len):
                action = self.select_action(state)
                next_state, reward, done, info = self.game.step(action)
                self.replay_memory.push((state, action, next_state, reward,done))
                episode_reward += reward 
                

                # Updates when memory is fully stored.
                if len(self.replay_memory.memory) >= capacity:
                  self.update()
                
                state = next_state

                # Updating weights of target network.
                if timestep % self.update_weights == 0:
                   self.target_net.load_state_dict(self.train_net.state_dict()) 

                if done == True:
                  break


            print("Episode: {}, Rewards: {}".format(epoch, episode_reward))
            reward_list.append(episode_reward)

player = Agent(game, DQN = Neural_Net())
train = player.learn(num_epochs =20000, episode_len =10000)

plt.plot(reward_list, label ='Episodic Rewards')
plt.ylabel('Rewards')
plt.xlabel('Number of Episodes')
ylim, ymax = plt.ylim(bottom =0, top=1)
xmin, xmax = plt.xlim(left =0, right=200)        # Plotting graph for first 200 episodes.
plt.legend()
plt.show()
reward_mean = np.mean(reward_list)
print(reward_mean)                               # Average reward
print(len(reward_list))