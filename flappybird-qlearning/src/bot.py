import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class Bot(object):
    """
    The Bot class that applies the Qlearning logic to Flappy bird game
    After every iteration (iteration = 1 game that ends with the bird dying) updates Q values
    After every DUMPING_N iterations, dumps the Q values to the local JSON file
    """

    def __init__(self):
        self.gameCNT = 0  # Game count of current run, incremented after every death
        self.DUMPING_N = 25  # Number of iterations to dump Q values to JSON after
        self.discount = 1.0
        self.r = {0: 1, 1: -1000}  # Reward function
        self.lr = 0.7
        self.load_qvalues()
        self.last_state = "420_240_0"
        self.last_action = 0
        self.moves = []

    def load_qvalues(self):
        """
        Load q values from a JSON file
        """
        self.qvalues = {}
        try:
            fil = open(f"{DATA_DIR}/qvalues.json", "r")
        except IOError:
            return
        self.qvalues = json.load(fil)
        fil.close()

    def act(self, xdif, ydif, vel):
        """
        Chooses the best action with respect to the current state - Chooses 0 (don't flap) to tie-break
        """
        state = self.map_state(xdif, ydif, vel)

        self.moves.append((self.last_state, self.last_action, state))  # Add the experience to the history

        self.last_state = state  # Update the last_state with the current state

        # 缓存局部变量，减少多次字典访问
        q0, q1 = self.qvalues[state]
        action = 0 if q0 >= q1 else 1
        self.last_action = action

        return action

    def update_scores(self, dump_qvalues=True):
        """
        Update qvalues via iterating over experiences
        """
        history = list(reversed(self.moves))

        # 缓存局部变量
        qvalues = self.qvalues
        lr = self.lr
        discount = self.discount
        r0 = self.r[0]
        r1 = self.r[1]

        # Flag if the bird died in the top pipe
        high_death_flag = True if int(history[0][2].split("_")[1]) > 120 else False

        # Q-learning score updates
        t = 1
        for state, act, res_state in history:
            # Select reward
            if t == 1 or t == 2:
                cur_reward = r1
            elif high_death_flag and act:
                cur_reward = r1
                high_death_flag = False
            else:
                cur_reward = r0

            # Q-learning 更新
            old_val = qvalues[state][act]
            q_max = max(qvalues[res_state])
            self.qvalues[state][act] = (1 - lr) * old_val + lr * (cur_reward + discount * q_max)

            t += 1

        self.gameCNT += 1  # increase game count
        if dump_qvalues:
            self.dump_qvalues()  # Dump q values (if game count % DUMPING_N == 0)
        self.moves = []  # clear history after updating strategies

    def map_state(self, xdif, ydif, vel):
        """
        Map the (xdif, ydif, vel) to a grid state.
        Optimized: 使用局部变量缓存整型转换结果，减少重复计算。
        """
        xdif = int(xdif)
        ydif = int(ydif)

        # 根据不同范围设置不同的网格步长
        if xdif < 140:
            xdif -= xdif % 10
        else:
            xdif -= xdif % 70

        if ydif < 180:
            ydif -= ydif % 10
        else:
            ydif -= ydif % 60

        return f"{xdif}_{ydif}_{vel}"

    def dump_qvalues(self, force=False):
        """
        Dump the qvalues to the JSON file
        """
        if self.gameCNT % self.DUMPING_N == 0 or force:
            fil = open(f"{DATA_DIR}/qvalues.json", "w")
            json.dump(self.qvalues, fil)
            fil.close()
            logging.debug("Q-values updated on local file.")
