from pathlib import Path

import pygame

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"


def load():
    # 玩家精灵不同状态的图片路径
    PLAYER_PATH = (
        f"{ASSET_DIR}/sprites/redbird-upflap.png",
        f"{ASSET_DIR}/sprites/redbird-midflap.png",
        f"{ASSET_DIR}/sprites/redbird-downflap.png",
    )

    # 背景图片路径
    BACKGROUND_PATH = f"{ASSET_DIR}/sprites/background-black.png"

    # 管道图片路径
    PIPE_PATH = f"{ASSET_DIR}/sprites/pipe-green.png"

    IMAGES, SOUNDS, HITMASKS = {}, {}, {}

    # 分数字符串精灵（数字0-9）
    IMAGES["numbers"] = (
        pygame.image.load(f"{ASSET_DIR}/sprites/0.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/1.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/2.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/3.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/4.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/5.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/6.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/7.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/8.png").convert_alpha(),
        pygame.image.load(f"{ASSET_DIR}/sprites/9.png").convert_alpha(),
    )

    # 地面图片路径
    IMAGES["base"] = pygame.image.load(f"{ASSET_DIR}/sprites/base.png").convert_alpha()

    # 声音部分（目前注释掉）
    # if "win" in sys.platform:
    #     soundExt = ".wav"
    # else:
    #     soundExt = ".ogg"
    # SOUNDS["die"] = pygame.mixer.Sound(f"{asset_dir}/audio/die" + soundExt)
    # SOUNDS["hit"] = pygame.mixer.Sound(f"{asset_dir}/audio/hit" + soundExt)
    # SOUNDS["point"] = pygame.mixer.Sound(f"{asset_dir}/audio/point" + soundExt)
    # SOUNDS["swoosh"] = pygame.mixer.Sound(f"{asset_dir}/audio/swoosh" + soundExt)
    # SOUNDS["wing"] = pygame.mixer.Sound(f"{asset_dir}/audio/wing" + soundExt)

    # 背景精灵
    IMAGES["background"] = pygame.image.load(BACKGROUND_PATH).convert()

    # 玩家精灵
    IMAGES["player"] = (
        pygame.image.load(PLAYER_PATH[0]).convert_alpha(),
        pygame.image.load(PLAYER_PATH[1]).convert_alpha(),
        pygame.image.load(PLAYER_PATH[2]).convert_alpha(),
    )

    # 管道精灵，分别为颠倒和正常状态
    IMAGES["pipe"] = (
        pygame.transform.rotate(pygame.image.load(PIPE_PATH).convert_alpha(), 180),
        pygame.image.load(PIPE_PATH).convert_alpha(),
    )

    # 管道的碰撞检测遮罩
    HITMASKS["pipe"] = (getHitmask(IMAGES["pipe"][0]), getHitmask(IMAGES["pipe"][1]))

    # 玩家精灵的碰撞检测遮罩
    HITMASKS["player"] = (
        getHitmask(IMAGES["player"][0]),
        getHitmask(IMAGES["player"][1]),
        getHitmask(IMAGES["player"][2]),
    )

    return IMAGES, SOUNDS, HITMASKS


def getHitmask(image):
    """返回一个基于图片 alpha 通道的碰撞遮罩。"""
    mask = []
    for x in range(image.get_width()):
        mask.append([])
        for y in range(image.get_height()):
            mask[x].append(bool(image.get_at((x, y))[3]))
    return mask
