import os
import pickle
import random
import sys
from collections import deque
from itertools import cycle
from pathlib import Path

import pygame
from tqdm import tqdm

sys.path.append(os.getcwd())

import cProfile
import io
import logging
import pstats
import time

from bot import Bot

DEBUG = False  # 将DEBUG设置为False以禁用DEBUG消息
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
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
    global HITMASKS, bot

    # 确保日志级别设置正确
    logging.getLogger().setLevel(logging.DEBUG if DEBUG else logging.INFO)

    # load dumped HITMASKS
    data_dir = Path(__file__).resolve().parent.parent / "data"
    with open(f"{data_dir}/hitmasks_data.pkl", "rb") as input:
        HITMASKS = pickle.load(input)

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

    return {"playery": playery + playerShmVals["val"], "basex": basex, "playerIndexGen": playerIndexGen}


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
        crashTest = checkCrash({"x": playerx, "y": playery, "index": playerIndex}, upperPipes, lowerPipes)
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
        logging.debug("\nTime taken: " + str(end_time - start_time))
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


def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collders with base or pipes."""
    pi = player["index"]
    player["w"] = PLAYER[IM_WIDTH]
    player["h"] = PLAYER[IM_HEIGTH]

    # if player crashes into ground
    if (player["y"] + player["h"] >= BASEY - 1) or (player["y"] + player["h"] <= 0):
        return [True, True]

    playerRect = pygame.Rect(player["x"], player["y"], player["w"], player["h"])
    pipeW = PIPE[IM_WIDTH]
    pipeH = PIPE[IM_HEIGTH]

    pHitMask = HITMASKS["player"][pi]
    uHitmask = HITMASKS["pipe"][0]
    lHitmask = HITMASKS["pipe"][1]

    for uPipe, lPipe in zip(upperPipes, lowerPipes):
        # upper and lower pipe rects
        uPipeRect = pygame.Rect(uPipe["x"], uPipe["y"], pipeW, pipeH)
        lPipeRect = pygame.Rect(lPipe["x"], lPipe["y"], pipeW, pipeH)

        # if bird collided with upipe or lpipe
        if pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask) or pixelCollision(
            playerRect, lPipeRect, pHitMask, lHitmask
        ):
            return [True, False]

    return [False, False]


def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y

    hitmask1_sub = hitmask1[x1 : x1 + rect.width]
    hitmask2_sub = hitmask2[x2 : x2 + rect.width]

    for hitmask1_row, hitmask2_row in zip(hitmask1_sub, hitmask2_sub):
        if any(
            h1 and h2
            for h1, h2 in zip(hitmask1_row[y1 : y1 + rect.height], hitmask2_row[y2 : y2 + rect.height])
        ):
            return True
    return False


if __name__ == "__main__":
    main()

    if DEBUG:
        pr.disable()
        output_dir = Path(__file__).resolve().parent / "benchmark"
        pr.dump_stats(f"{output_dir}/pipeline-bot.prof")
        os.system(f"python -m flameprof {output_dir}/pipeline-bot.prof > {output_dir}/pipeline-bot.svg")
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
        ps.print_stats()
        print(s.getvalue())
