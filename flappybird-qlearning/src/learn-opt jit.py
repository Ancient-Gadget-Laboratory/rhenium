import os
import pickle
import random
import sys
from collections import deque
from itertools import cycle
from pathlib import Path
from tqdm import tqdm

sys.path.append(os.getcwd())

import cProfile
import io
import logging
import pstats
import time

import numba as nb
import numpy as np
from bot import Bot

DEBUG = False  # 将DEBUG设置为False以禁用DEBUG消息
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
start_time = time.time()

if DEBUG:
    pr = cProfile.Profile()
    pr.enable()

# Initialize the bot
bot = Bot()

SCREENWIDTH = 288
SCREENHEIGHT = 512
# amount by which base can maximum shift to left
PIPEGAPSIZE = 100  # gap between upper and lower part of pipe
BASEY = SCREENHEIGHT * 0.79

# image width height indices for ease of use
IM_WIDTH = 0
IM_HEIGTH = 1
# image, Width, Height
PIPE = [52, 320]
PLAYER = [34, 24]
BASE = [336, 112]
BACKGROUND = [288, 512]

# running setup
ITERATIONS = 3000
VERBOSE = False

# tqdm setup
iter_range = tqdm(range(ITERATIONS), desc="Game Count", colour="red")

def main():
    global HITMASKS, bot, HITMASKS_NP

    # 确保日志级别设置正确
    logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

    # load dumped HITMASKS
    data_dir = Path(__file__).resolve().parent.parent / "data"
    with open(f"{data_dir}/hitmasks_data.pkl", "rb") as input:
        HITMASKS = pickle.load(input)

    HITMASKS_NP = {
        "player": [np.asarray(mask) for mask in HITMASKS["player"]],
        "pipe": [np.asarray(mask) for mask in HITMASKS["pipe"]],
    }

    IS_RUNNING = True

    while IS_RUNNING:
        movementInfo = showWelcomeAnimation()
        crashInfo = mainGame(movementInfo)
        iter_range.update(1)
        IS_RUNNING = showGameOverScreen(crashInfo)


def showWelcomeAnimation():
    """Shows welcome screen animation of flappy bird"""
    # index of player to blit on screen
    playerIndexGen = cycle([0, 1, 2, 1])
    playery = int((SCREENHEIGHT - PLAYER[IM_HEIGTH]) / 2)
    basex = 0

    # player shm for up-down motion on welcome screen
    playerShmVals = {"val": 0, "dir": 1}

    return {
        "playery": playery + playerShmVals["val"],
        "basex": basex,
        "playerIndexGen": playerIndexGen,
    }


def mainGame(movementInfo):
    score = 0
    playerIndex = 0
    loopIter = 0
    playerIndexGen = movementInfo["playerIndexGen"]

    # 缓存常量
    playerx = int(SCREENWIDTH * 0.2)
    playery = movementInfo["playery"]
    basex = movementInfo["basex"]
    baseShift = BASE[IM_WIDTH] - BACKGROUND[IM_WIDTH]

    # 缓存图像宽高，减少索引开销
    player_w = PLAYER[IM_WIDTH]
    player_h = PLAYER[IM_HEIGTH]
    pipe_w = PIPE[IM_WIDTH]
    # pipe_h = PIPE[IM_HEIGTH]  # 如有需要

    # 获取两组管道，初始化管道队列
    newPipe1 = getRandomPipe()
    newPipe2 = getRandomPipe()
    upperPipes = deque(
        [
            {"x": SCREENWIDTH + 200, "y": newPipe1[0]["y"]},
            {"x": SCREENWIDTH + 200 + (SCREENWIDTH / 2), "y": newPipe2[0]["y"]},
        ]
    )
    lowerPipes = deque(
        [
            {"x": SCREENWIDTH + 200, "y": newPipe1[1]["y"]},
            {"x": SCREENWIDTH + 200 + (SCREENWIDTH / 2), "y": newPipe2[1]["y"]},
        ]
    )

    # 运动参数
    pipeVelX = -4
    playerVelY = -9
    playerMaxVelY = 10
    playerAccY = 1
    playerFlapAcc = -9
    playerFlapped = False

    while True:
        # 采用局部变量减少字典访问
        lower0_x = lowerPipes[0]["x"]
        # 选择目标管道
        if -playerx + lower0_x > -30:
            myPipe = lowerPipes[0]
        else:
            myPipe = lowerPipes[1]

        # 执行动作判断
        if bot.act(-playerx + myPipe["x"], -playery + myPipe["y"], playerVelY):
            if playery > -2 * player_h:
                playerVelY = playerFlapAcc
                playerFlapped = True

        # 检查碰撞
        crashTest = checkCrash(
            {"x": playerx, "y": playery, "index": playerIndex}, upperPipes, lowerPipes
        )
        if crashTest[0]:
            bot.update_scores(dump_qvalues=False)
            return {
                "y": playery,
                "groundCrash": crashTest[1],
                "basex": basex,
                "upperPipes": upperPipes,
                "lowerPipes": lowerPipes,
                "score": score,
                "playerVelY": playerVelY,
            }

        # 更新分数：提前计算玩家中点
        playerMidPos = playerx + player_w / 2
        for pipe in upperPipes:
            pipeMidPos = pipe["x"] + pipe_w / 2
            # 只需要检测一次进入区间
            if pipeMidPos <= playerMidPos < pipeMidPos + 4:
                score += 1

        # 更新动画帧和基座位置
        if (loopIter + 1) % 3 == 0:
            playerIndex = next(playerIndexGen)
        loopIter = (loopIter + 1) % 30
        basex = -((-basex + 100) % baseShift)

        # 玩家运动逻辑：局部变量计算
        if playerVelY < playerMaxVelY and not playerFlapped:
            playerVelY += playerAccY
        if playerFlapped:
            playerFlapped = False
        # 确保不会超过地面
        playery += min(playerVelY, BASEY - playery - player_h)

        # 移动所有管道
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            uPipe["x"] += pipeVelX
            lPipe["x"] += pipeVelX

        # 当第一个管道即将进入屏幕时添加新的管道
        if 0 < upperPipes[0]["x"] < 5:
            newPipe = getRandomPipe()
            upperPipes.append(newPipe[0])
            lowerPipes.append(newPipe[1])

        # 如果第一个管道完全移出屏幕，移除该管道
        if upperPipes[0]["x"] < -pipe_w:
            upperPipes.popleft()
            lowerPipes.popleft()


def showGameOverScreen(crashInfo):
    if VERBOSE:
        score = crashInfo["score"]
        logging.debug(str(bot.gameCNT - 1) + " | " + str(score))

    if bot.gameCNT == (ITERATIONS):
        logging.debug("\nGame Over\n")
        bot.dump_qvalues(force=True)
        end_time = time.time()
        logging.debug("Time taken: " + str(end_time - start_time))
        return False

    return True


def playerShm(playerShm):
    """oscillates the value of playerShm['val'] between 8 and -8"""
    if abs(playerShm["val"]) == 8:
        playerShm["dir"] *= -1

    if playerShm["dir"] == 1:
        playerShm["val"] += 1
    else:
        playerShm["val"] -= 1


def getRandomPipe():
    """returns a randomly generated pipe"""
    # y of gap between upper and lower pipe
    gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
    gapY += int(BASEY * 0.2)
    pipeHeight = PIPE[IM_HEIGTH]
    pipeX = SCREENWIDTH + 10

    return [
        {"x": pipeX, "y": gapY - pipeHeight},  # upper pipe
        {"x": pipeX, "y": gapY + PIPEGAPSIZE},  # lower pipe
    ]


@nb.njit(fastmath=True)
def pixelCollision_numba(x1, y1, w1, h1, hitmask1, x2, y2, w2, h2, hitmask2):
    """
    Numba 优化的像素碰撞检测。
    rect1: (x1, y1, w1, h1)，rect2: (x2, y2, w2, h2)
    参数均应为整数，hitmask* 为二维 bool 数组
    """
    # 假定传入时 x1,y1,...已经是 int 型，不再重复转换
    inter_x = x1 if x1 >= x2 else x2  # max(x1, x2)
    inter_y = y1 if y1 >= y2 else y2  # max(y1, y2)
    inter_x2 = x1 + w1 if (x1 + w1) < (x2 + w2) else (x2 + w2)  # min(x1+w1, x2+w2)
    inter_y2 = y1 + h1 if (y1 + h1) < (y2 + h2) else (y2 + h2)  # min(y1+h1, y2+h2)

    if inter_x2 <= inter_x or inter_y2 <= inter_y:
        return False

    # 计算交集区域起始索引和尺寸
    start1_x = inter_x - x1
    start1_y = inter_y - y1
    start2_x = inter_x - x2
    start2_y = inter_y - y2
    inter_width = inter_x2 - inter_x
    inter_height = inter_y2 - inter_y

    for i in range(inter_width):
        for j in range(inter_height):
            if (
                hitmask1[start1_x + i, start1_y + j]
                and hitmask2[start2_x + i, start2_y + j]
            ):
                return True
    return False


@nb.njit(fastmath=True)
def checkPipeCollision_numba(
    player_x,
    player_y,
    player_w,
    player_h,
    pipe_x,
    pipe_y,
    pipe_w,
    pipe_h,
    hitmask_player,
    hitmask_pipe,
):
    """
    调用 numba 优化后的像素碰撞检测，并传入已转换为 int 的参数
    """
    return pixelCollision_numba(
        player_x,
        player_y,
        player_w,
        player_h,
        hitmask_player,
        pipe_x,
        pipe_y,
        pipe_w,
        pipe_h,
        hitmask_pipe,
    )


def checkCrash(player, upperPipes, lowerPipes):
    """
    检测玩家与管道是否碰撞：
    如果撞地面或飞出上界直接返回；否则对每个管道调用 numba 加速的碰撞检测。
    """
    # 假设全局变量 PLAYER、BASEY、PIPE 已定义
    player["w"] = PLAYER[IM_WIDTH]
    player["h"] = PLAYER[IM_HEIGTH]

    if (player["y"] + player["h"] >= BASEY - 1) or (player["y"] <= 0):
        return [True, True]

    # 准备好玩家的矩形（均为 int 型）
    player_x = int(player["x"])
    player_y = int(player["y"])
    player_w = int(player["w"])
    player_h = int(player["h"])

    pipeW = int(PIPE[IM_WIDTH])
    pipeH = int(PIPE[IM_HEIGTH])

    # 从预转换的 HITMASKS_NP 中获取对应的 NumPy 数组，不再重复转换
    pi = player["index"]
    hitmask_player = HITMASKS_NP["player"][pi]
    uHitmask = HITMASKS_NP["pipe"][0]
    lHitmask = HITMASKS_NP["pipe"][1]

    for uPipe, lPipe in zip(upperPipes, lowerPipes):
        # 管道的矩形均转为 int 型
        u_x = int(uPipe["x"])
        u_y = int(uPipe["y"])
        l_x = int(lPipe["x"])
        l_y = int(lPipe["y"])
        if checkPipeCollision_numba(
            player_x,
            player_y,
            player_w,
            player_h,
            u_x,
            u_y,
            pipeW,
            pipeH,
            hitmask_player,
            uHitmask,
        ) or checkPipeCollision_numba(
            player_x,
            player_y,
            player_w,
            player_h,
            l_x,
            l_y,
            pipeW,
            pipeH,
            hitmask_player,
            lHitmask,
        ):
            return [True, False]
    return [False, False]


if __name__ == "__main__":
    main()

    if DEBUG:
        pr.disable()
        output_dir = Path(__file__).resolve().parent / "benchmark"
        pr.dump_stats(f"{output_dir}/pipeline-jit.prof")
        os.system(
            f"python -m flameprof {output_dir}/pipeline-jit.prof > {output_dir}/pipeline-jit.svg"
        )
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
        ps.print_stats()
        print(s.getvalue())
