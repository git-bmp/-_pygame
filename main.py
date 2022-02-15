try:
    import pygame_sdl2
    pygame_sdl2.import_as_pygame()
except ImportError:
    pass

import random, sys, copy, os, pygame
from pygame.locals import *
import queue
import json
import pickle
from enum import Enum


class GameStateItem(Enum):
    SELECTED_STAR_INDEX = 4


class Settings:
    """保存当前关卡索引，在全屏之前保存窗口的宽和高"""
    def __init__(self):
        self.current_level_index = 0  # 63
        self.window_width = 0
        self.window_height = 0
        self.fullscreen = True

    def save(self):
        """保存设置到文件中"""
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.__dict__, f, sort_keys=True, indent=4)
        except Exception as e:
            print("Error settings.save(): {}".format(str(e)))

    def load(self):
        """从文件内到处设置"""
        try:
            with open('settings.json', 'r') as f:
                self.__dict__ = json.load(f)
        except Exception as e:
            print("Error settings.load(): {}".format(str(e)))


class Button(object):
    def __init__(self, upimage, downimage, position):
        self.image_up = pygame.image.load(upimage).convert_alpha()  # 透明转换
        self.image_down = pygame.image.load(downimage).convert_alpha()
        self.position = position
        self.button_out = True

    def is_over(self):
        point_x, point_y = pygame.mouse.get_pos()
        x, y = self.position
        width, height = self.image_up.get_size()
        x -= width/2
        y -= height/2

        in_x = x < point_x < x + width
        in_y = y < point_y < y + height
        return in_x and in_y

    def render(self, surface):
        x, y = self.position
        width, height = self.image_up.get_size()
        x -= width/2
        y -= height/2
        if self.is_over():
            surface.blit(self.image_down, (x, y))
            if self.button_out == True:
                self.button_out = False
        else:
            surface.blit(self.image_up, (x, y))
            self.button_out = True


settings = Settings()
settings.load()


# FPS = 30 # 30帧每秒更新屏幕
def set_window_size(size, fullscreen=False):
    global DISPLAYSURF, WINWIDTH, WINHEIGHT, HALF_WINWIDTH, HALF_WINHEIGHT
    x, y = size   # x,y的值靠值传递获得
    if fullscreen:
        DISPLAYSURF = pygame.display.set_mode((0, 0), HWSURFACE | DOUBLEBUF | FULLSCREEN)   # flag参数用来控制想要的显示类型，用'|'来组合类型  set_mode()控制宽度与高度，（0,0）选择SDL 版本 1.2.10 or above
    else:
        DISPLAYSURF = pygame.display.set_mode(size, HWSURFACE | DOUBLEBUF | RESIZABLE)  # FULLSCREEN    create a fullscreen display   DOUBLEBUF     recommended for HWSURFACE or OPENGL   # HWSURFACE     hardware accelerated, only in FULLSCREEN
    x, y = pygame.display.get_surface().get_size()
    WINWIDTH = x  # 窗口程序的宽
    WINHEIGHT = y
    HALF_WINWIDTH = int(x / 2)
    HALF_WINHEIGHT = int(y / 2)
    if not fullscreen:  # 离开全屏后，窗口返回原来尺寸
        settings.window_width = x
        settings.window_height = y
    settings.fullscreen = fullscreen

# 每一块地砖的宽度和高度
TILEWIDTH = 50
TILEHEIGHT = 85
TILEFLOORHEIGHT = 42

CAM_MOVE_SPEED = 2  # 镜头移动每帧多少像素


# 墙外地砖附加额外装饰的百分率，例如树或者势头，下面是百分之20
OUTSIDE_DECORATION_PCT = 20

BRIGHTBLUE = (0, 170, 255)
WHITE      = (255, 255, 255)
BLACK      = (100, 100, 100)
STARTCREEN = (0, 0, 0)
BGCOLOR = BLACK
TEXTCOLOR = WHITE

UP = 'up'
DOWN = 'down'
LEFT = 'left'
RIGHT = 'right'


def main():
    global FPSCLOCK, DISPLAYSURF, IMAGESDICT, TILEMAPPING, OUTSIDEDECOMAPPING, BASICFONT, PLAYERIMAGES, currentImage, savedGameStateObj

    # 初始化pygame并且设置全局变量
    pygame.init()
    pygame.mixer.init()

    # 设置背景播放音乐
    pygame.mixer.music.load("bg_music.ogg")
    pygame.mixer.music.set_volume(0.01)
    pygame.mixer.music.play(3)

    # 设置两种不同的音效
    move_sound = pygame.mixer.Sound("move_sound.wav")
    move_sound.set_volume(0.9)
    success_sound = pygame.mixer.Sound("success_sound.wav")
    success_sound.set_volume(0.1)
    FPSCLOCK = pygame.time.Clock()  # 创建一个新的Clock对象并且该对象被使用来跟踪一段时间

    # 因为存储在DISPLAYSURF中的Surface对象是从pygame.display.set_mode()函数返回的,
    # 当 pygame.display.update(）函数被调用时这个surface对象被绘制到实际计算机屏幕中。
    set_window_size((settings.window_width, settings.window_height), settings.fullscreen)
    # DISPLAYSURF = pygame.display.set_mode((WINWIDTH, WINHEIGHT),HWSURFACE|DOUBLEBUF|FULLSCREEN)

    pygame.display.set_caption('经典推箱子')  # 设置窗口标题
    # BASICFONT = pygame.font.Font('freesansbold.ttf', 18)
    BASICFONT = pygame.font.Font("yxcbft.ttf", 30)

    # A global dict value that will contain all the Pygame
    # Surface objects returned by pygame.image.load().图片函数
    # 字典键是Surface对象，值是导入
    IMAGESDICT = {'uncovered goal': pygame.image.load('RedSelector.png'),
                  'covered goal': pygame.image.load('Selector.png'),
                  'star': pygame.image.load('Star.png'),
                  'star red': pygame.image.load('star_red.png'),
                  'corner': pygame.image.load('Wall_Block_Tall.png'),
                  'wall': pygame.image.load('Wood_Block_Tall.png'),
                  'inside floor': pygame.image.load('Plain_Block.png'),
                  'outside floor': pygame.image.load('Grass_Block.png'),
                  'title': pygame.image.load('star_title.png'),
                  'solved': pygame.image.load('star_solved.png'),
                  'princess': pygame.image.load('princess.png'),
                  'boy': pygame.image.load('boy.png'),
                  'catgirl': pygame.image.load('catgirl.png'),
                  'horngirl': pygame.image.load('horngirl.png'),
                  'pinkgirl': pygame.image.load('pinkgirl.png'),
                  'rock': pygame.image.load('Rock.png'),
                  'short tree': pygame.image.load('Tree_Short.png'),
                  'tall tree': pygame.image.load('Tree_Tall.png'),
                  'ugly tree': pygame.image.load('Tree_Ugly.png')}

    # 这些字典值时全局类型的，映射到关卡文件出现的字符，这些字符代表Surface对象
    TILEMAPPING = {'x': IMAGESDICT['corner'],
                   '#': IMAGESDICT['wall'],
                   'o': IMAGESDICT['inside floor'],
                   ' ': IMAGESDICT['outside floor']}
    OUTSIDEDECOMAPPING = {'1': IMAGESDICT['rock'],
                          '2': IMAGESDICT['short tree'],
                          '3': IMAGESDICT['tall tree'],
                          '4': IMAGESDICT['ugly tree']}

    # 玩家图片与下表的对应，透过下标更换玩家图片
    currentImage = 0
    PLAYERIMAGES = [IMAGESDICT['princess'],
                    IMAGESDICT['boy'],
                    IMAGESDICT['catgirl'],
                    IMAGESDICT['horngirl'],
                    IMAGESDICT['pinkgirl']]

    startScreen()  # 展现标题屏幕页面，直到用户按下按键

    # 读取关卡文件
    levels = readLevelsFile('starPusherLevels.txt')
    # 保存游戏状态(玩家、箱子在哪里,步数)
    savedGameStateObj = None


    # try:
    #     with open('gameStateObj.pkl', 'rb') as f:  # 查询了解pkl文件
    #         savedGameStateObj = pickle.load(f)
    # except Exception as e:
    #     print("Error loading gameStateObj.pkl: {}".format(str(e)))

    # 游戏主循环，一个关卡对应一次循环，当用户完成当前关卡，上/下关卡被导入
    while True:
        result = runLevel(levels, settings.current_level_index, move_sound, success_sound)
        # try:
        #     result = runLevel(levels, settings.current_level_index)
        # except Exception as ex:
        #     print("Error in runLevel, retrying without savedGameStateObj: {}".format(str(ex)))
        savedGameStateObj = None
        if result in ('solved', 'next'):
            # Go to the next level.
            settings.current_level_index += 1
            if settings.current_level_index >= len(levels):
                # If there are no more levels, go back to the first one.
                settings.current_level_index = 0
        elif result == 'back':
            # Go to the previous level.
            settings.current_level_index -= 1
            if settings.current_level_index < 0:
                # If there are no previous levels, go to the last one.
                settings.current_level_index = len(levels)-1
        elif result == 'reset':
            pass  # Do nothing. Loop re-calls runLevel() to reset the level


def runLevel(levels, levelNum, move_sound, success_sound):
    global currentImage, gameStateObj
    upButton = Button('up_Button_start.png', 'up_Button_down.png', (150, 300))
    downButton = Button('down_Button_start.png', 'down_Button_down.png', (150, 480))
    leftButton = Button('left_Button_start.png', 'left_Button_down.png', (50, 390))
    rightButton = Button('right_Button_start.png', 'right_Button_down.png', (250, 390))
    nextButton = Button('next_Button_start.png', 'next_Button_down.png', (WINWIDTH*18/20, 210))
    backButton = Button('back_Button_start.png', 'back_Button_down.png', (WINWIDTH*18/20, 150))
    resetButton = Button('reset_Button_start.png', 'reset_Button_down.png', (WINWIDTH*18/20, 350))
    revButton = Button('rev_Button_start.png', 'rev_Button_down.png', (WINWIDTH*18/20, 410))
    helpButton = Button('help_Button_start.png', 'help_Button_down.png', (WINWIDTH*18/20, 550))
    levelObj = levels[levelNum]
    gameStateObj = copy.deepcopy(levelObj['startState'])
    if savedGameStateObj != None:
        gameStateObj = savedGameStateObj
    mapObj = decorateMap(levelObj['mapObj'], gameStateObj['player'])
    mapWidth = len(mapObj) * TILEWIDTH
    mapHeight = (len(mapObj[0]) - 1) * TILEFLOORHEIGHT + TILEHEIGHT
    MAX_CAM_X_PAN = abs(HALF_WINHEIGHT - int(mapHeight / 2)) + TILEWIDTH
    MAX_CAM_Y_PAN = abs(HALF_WINWIDTH - int(mapWidth / 2)) + TILEHEIGHT
    mapNeedsRedraw = True  # 设置为True去调用drawMap函数
    levelIsComplete = False
    cameraOffsetX = 0  # 追踪相机移动距离
    cameraOffsetY = 0
    cameraUp = False  # 追踪相机键是否被按下
    cameraDown = False
    cameraLeft = False
    cameraRight = False
    playerMoveTo = None
    mousex = 0
    mousey = 0
    mouseTileX = 0
    mouseTileY = 0
    jump = 0
    gameStateObjHistory = []
    gameStateObjRedoList = []
    while True:
        playerMoveRepeat = 1  # 重置以下变量:
        keyPressed = False
        isRedo = False
        isUndo = False
        DISPLAYSURF.fill(BGCOLOR)
        upButton.render(DISPLAYSURF)
        downButton.render(DISPLAYSURF)
        leftButton.render(DISPLAYSURF)
        rightButton.render(DISPLAYSURF)
        nextButton.render(DISPLAYSURF)
        backButton.render(DISPLAYSURF)
        resetButton.render(DISPLAYSURF)
        revButton.render(DISPLAYSURF)
        helpButton.render(DISPLAYSURF)

        for event in pygame.event.get():  # 事件处理
            if event.type == QUIT:
                terminate()  # 玩家店家窗口的"X"
            elif event.type == VIDEORESIZE:
                mapNeedsRedraw = True
                set_window_size(event.dict['size'])
                MAX_CAM_X_PAN = abs(HALF_WINHEIGHT - int(mapHeight / 2)) + TILEWIDTH
                MAX_CAM_Y_PAN = abs(HALF_WINWIDTH - int(mapWidth / 2)) + TILEHEIGHT
            if event.type == pygame.MOUSEBUTTONUP:
                keyPressed = True
                if levelIsComplete:
                    return 'solved'
                if upButton.is_over():
                    move_sound.play()
                    playerMoveTo = UP
                if downButton.is_over():
                    move_sound.play()
                    playerMoveTo = DOWN
                if leftButton.is_over():
                    move_sound.play()
                    playerMoveTo = LEFT
                if rightButton.is_over():
                    move_sound.play()
                    playerMoveTo = RIGHT
                if nextButton.is_over():
                    return 'next'
                if backButton.is_over():
                    return 'back'
                if resetButton.is_over():
                    return 'reset'
                if revButton.is_over():  # 返回上一步
                    if len(gameStateObjRedoList) > 0:
                        gameStateObj = gameStateObjRedoList.pop()
                        isRedo = True
                    if len(gameStateObjHistory) > 1:
                        gameStateObjRedoList.append(gameStateObj)
                        gameStateObjHistory.pop()
                        gameStateObj = gameStateObjHistory.pop()
                        isUndo = True
                if helpButton.is_over():
                    helpScreen()
                mapNeedsRedraw = True
                # if y < int(WINHEIGHT / 3): playerMoveTo = UP
                # elif y > int(WINHEIGHT / 3 * 2): playerMoveTo = DOWN
                # else:
                #     if x < int(WINWIDTH / 2): playerMoveTo = LEFT
                #     else: playerMoveTo = RIGHT
                mousex, mousey = pygame.mouse.get_pos()  # 返回鼠标当前的坐标(x,y)position
                if cameraOffsetX == 0:
                    cameraOffsetX_tiles = 0
                else:
                    cameraOffsetX_tiles = cameraOffsetX / TILEWIDTH
                cameraOffsetY_tiles = 0 if cameraOffsetY == 0 else cameraOffsetY / TILEFLOORHEIGHT
                mouseTileX = (0 if mousex - HALF_WINWIDTH == 0 else (mousex - HALF_WINWIDTH) / TILEWIDTH)  + len(mapObj) / 2 - .5 - cameraOffsetX_tiles
                mouseTileY = (mousey - HALF_WINHEIGHT) / (TILEFLOORHEIGHT) + len(mapObj[0]) / 2 - .5 - cameraOffsetY_tiles
                mouseTileX = int(round(mouseTileX, 0))
                mouseTileY = int(round(mouseTileY, 0))
                mouseTile = (mouseTileX, mouseTileY)
                if not isBlocked(mapObj, gameStateObj, mouseTileX, mouseTileY):
                    if gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] != None:
                        selectedStar = gameStateObj['stars'][gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]]
                        distance, player = pushStar(mapObj, gameStateObj, selectedStar, mouseTile) or (None, None)
                        if distance != None and distance > 0:
                            jump = distance
                            gameStateObj['stepCounter'] += distance
                            gameStateObj['player'] = player
                            # Move the star.
                            gameStateObj['stars'][gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]] = mouseTile
                    else:  # 即时传送
                        gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = None
                        # Create mesh, draw current location of stars:
                        mesh = copy.deepcopy(mapObj)
                        for star_x, star_y in gameStateObj['stars']:
                            mesh[star_x][star_y] = "$"
                        distance = BFS(mesh, gameStateObj['player'], mouseTile)
                        if not distance == None and distance > 0:
                            jump = distance
                            gameStateObj['stepCounter'] += distance
                            gameStateObj['player'] = mouseTile
                        else:
                            jump = 0
                elif mouseTile in gameStateObj['stars']:
                    # 选择或者取消选择星星
                    mouseTileStarIndex = gameStateObj['stars'].index(mouseTile)
                    if mouseTileStarIndex == gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]:
                        gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = None
                    else:
                        # 看玩家是否可以走到该处
                        mesh = copy.deepcopy(mapObj)
                        for star_x, star_y in gameStateObj['stars']: 
                            if not (star_x == mouseTileX and star_y == mouseTileY): mesh[star_x][star_y] = "$"
                        distance = BFS(mesh, gameStateObj['player'], mouseTile)
                        if not distance == None:
                            gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = mouseTileStarIndex
                else:  # 鼠标点击点在墙上
                    if gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] != None:
                        gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] = None
            elif event.type == KEYDOWN:
                if levelIsComplete:
                    return 'solved'
                mapNeedsRedraw = True
                keyPressed = True
                if event.key == K_z:
                    if (pygame.key.get_mods() & KMOD_CTRL) and (pygame.key.get_mods() & KMOD_SHIFT):  # 返回上一步
                        if len(gameStateObjRedoList) > 0:
                            gameStateObj = gameStateObjRedoList.pop()
                            isRedo = True
                    elif (pygame.key.get_mods() & KMOD_CTRL):  # 返回下一步
                        if len(gameStateObjHistory) > 1:
                            gameStateObjRedoList.append(gameStateObj)
                            gameStateObjHistory.pop()
                            gameStateObj = gameStateObjHistory.pop()
                            isUndo = True
                elif event.key == K_f:
                    set_window_size((settings.window_width, settings.window_height), not settings.fullscreen)
                    MAX_CAM_X_PAN = abs(HALF_WINHEIGHT - int(mapHeight / 2)) + TILEWIDTH
                    MAX_CAM_Y_PAN = abs(HALF_WINWIDTH - int(mapWidth / 2)) + TILEHEIGHT
                elif event.key == K_a:
                    cameraRight = True  # 设置相机移动模式
                elif event.key == K_d:
                    cameraLeft = True
                elif event.key == K_w:
                    cameraDown = True
                elif event.key == K_s:
                    cameraUp = True
                elif event.key == K_n:
                    return 'next'
                elif event.key == K_b:
                    return 'back'
                elif event.key == K_ESCAPE:
                    terminate()  # 按下“ESC”退出
                elif event.key == K_BACKSPACE:
                    return 'reset'  # 重置关卡.
                # elif event.key == K_AC_BACK: return 'reset' # Reset the level.
                elif event.key == K_p:
                    currentImage += 1  # 更改玩家角色
                    if currentImage >= len(PLAYERIMAGES):
                        currentImage = 0
                elif event.key == K_LEFT:
                    move_sound.play()  # 播放音效
                    playerMoveTo = LEFT
                elif event.key == K_RIGHT:
                    move_sound.play()
                    playerMoveTo = RIGHT
                elif event.key == K_UP:
                    move_sound.play()
                    playerMoveTo = UP
                elif event.key == K_DOWN:
                    move_sound.play()
                    playerMoveTo = DOWN
                if playerMoveTo != None:
                    if (pygame.key.get_mods() & KMOD_CTRL):   # get_mods()确定正在进行哪些修饰符键，返回一个整数，表示被持有的所有修饰符的位掩码。
                        playerMoveRepeat = 5    # 走5步
                    elif (pygame.key.get_mods() & KMOD_SHIFT):
                        playerMoveRepeat = 100  # 走到尽头，因为总长不足100步

            elif event.type == KEYUP:
                if event.key == K_a:
                    cameraRight = False  # 重置相机移动模式
                elif event.key == K_d:
                    cameraLeft = False
                elif event.key == K_w:
                    cameraDown = False
                elif event.key == K_s:
                    cameraUp = False
                elif event.key == K_UP or event.key == K_DOWN or event.key == K_LEFT or event.key == K_RIGHT:
                    playerMoveTo = None

        if keyPressed == False and (pygame.key.get_mods() & KMOD_ALT) == False:
            playerMoveTo = None

        if playerMoveTo != None and not levelIsComplete:
            # 按下移动键，玩家移动，并且把前方可推动的箱子推动
            countJump = True if playerMoveRepeat > 1 else False
            if countJump:
                jump = 0
            while playerMoveRepeat > 0:
                playerMoveRepeat -= 1
                moved = makeMove(mapObj, gameStateObj, playerMoveTo)
                if moved:
                    # 计步器计数
                    gameStateObj['stepCounter'] += 1
                    mapNeedsRedraw = True
                    if countJump:
                        jump += 1
                else:
                    playerMoveRepeat = 0

        # 关卡完成，显示关卡完成图片
        if mapNeedsRedraw and isLevelFinished(levelObj, gameStateObj):
            levelIsComplete = True
            success_sound.play()

        if len(gameStateObjHistory) == 0 \
            or gameStateObjHistory[len(gameStateObjHistory)-1]['player'] != gameStateObj['player'] \
            or gameStateObjHistory[len(gameStateObjHistory)-1][GameStateItem.SELECTED_STAR_INDEX.name] != gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]:
            gameStateObjHistory.append(copy.deepcopy(gameStateObj))
            if not isRedo and not isUndo and gameStateObjRedoList != []:
                gameStateObjRedoList = []
        if(len(gameStateObjHistory) > 300):
            for i in range(len(gameStateObjHistory) - 300):
                gameStateObjHistory.pop(0)

        # DISPLAYSURF.fill(BGCOLOR)
        #
        # upButton = Button('up_Button_start.png', 'up_Button_down.png', (150, 300))
        # upButton.render(DISPLAYSURF)


        if mapNeedsRedraw:
            mapSurf = drawMap(mapObj, gameStateObj, levelObj['goals'])
            mapNeedsRedraw = False

        if cameraUp and cameraOffsetY < MAX_CAM_X_PAN:
            cameraOffsetY += CAM_MOVE_SPEED
        elif cameraDown and cameraOffsetY > -MAX_CAM_X_PAN:
            cameraOffsetY -= CAM_MOVE_SPEED
        if cameraLeft and cameraOffsetX < MAX_CAM_Y_PAN:
            cameraOffsetX += CAM_MOVE_SPEED
        elif cameraRight and cameraOffsetX > -MAX_CAM_Y_PAN:
            cameraOffsetX -= CAM_MOVE_SPEED

        # 基于相机的偏移量适应 mapsurf 的矩形对象
        mapSurfRect = mapSurf.get_rect()
        mapSurfRect.center = (HALF_WINWIDTH + cameraOffsetX, HALF_WINHEIGHT + cameraOffsetY)

        # 重新绘制mapSurf到 DISPLAYSURF 表面中
        DISPLAYSURF.blit(mapSurf, mapSurfRect)

        levelSurf = BASICFONT.render('Level %s of %s' % (levelNum + 1, len(levels)), 1, TEXTCOLOR)
        levelRect = levelSurf.get_rect()
        levelRect.bottomleft = (20, WINHEIGHT - 10)
        DISPLAYSURF.blit(levelSurf, levelRect)
        stepSurf = BASICFONT.render('Steps: {}{}'.format(gameStateObj['stepCounter'], "" if jump < 2 else " +"+str(jump)), 1, TEXTCOLOR)
        stepRect = stepSurf.get_rect()
        stepRect.bottomleft = (20, WINHEIGHT - 60)
        DISPLAYSURF.blit(stepSurf, stepRect)
        debugSurf = BASICFONT.render('Player {} {}, Mouse {} {} ({} {}), Map {} {}, Camera: {} {}'.format(gameStateObj['player'][0], gameStateObj['player'][1], mouseTileX, mouseTileY, mousex, mousey, len(mapObj), len(mapObj[0]), cameraOffsetX, cameraOffsetY), 1, TEXTCOLOR)
        debugRect = debugSurf.get_rect()
        debugRect.bottomleft = (20, WINHEIGHT - 35)
        # DISPLAYSURF.blit(debugSurf, debugRect)
        if levelIsComplete:  # 关卡完成，显示完成图片，直到玩家按下其他按键.
            solvedRect = IMAGESDICT['solved'].get_rect()
            solvedRect.center = (HALF_WINWIDTH, HALF_WINHEIGHT)
            DISPLAYSURF.blit(IMAGESDICT['solved'], solvedRect)
            pygame.mixer.music.pause()

            pygame.mixer.music.play()

        pygame.display.update()  # 更新显示
        FPSCLOCK.tick()


def pushStar(mapObj, gameStateObj, src, dest):
    """如果箱子可以被推至目的地，返回一个元组（stepCount, player position）, 否则返回None"""
    src_x, src_y = src  # 选中的星星坐标
    mesh = copy.deepcopy(mapObj)
    for star_x, star_y in gameStateObj['stars']:
        if not (star_x == src_x and star_y == src_y):
            mesh[star_x][star_y] = "$"  # draw all stars accept the selected one
    if dest == None:  # see already if src adjoining cell can be reached by player
        return None
    dest_x, dest_y = dest
    if mesh[dest_x][dest_y] != 'o':
        return None
    visited = set()  # keep track of visited cells
    visited.add(src)  # Mark the source cell as visited
    q = queue.Queue()  # list to hold for each point: point currently holding the selected star, stepCount, player position
    q.put((src, 0, gameStateObj['player']))  # 0 steps to reach src
    while not q.empty():  # Do a BFS starting from source cell
        (point_x, point_y), distance, (player_x, player_y) = q.get()
        # 如果我们到达了目的地单元，我们这样做。If we have reached the destination cell, we are done..
        if point_x == dest_x and point_y == dest_y:
            return (distance, (player_x, player_y))
        # 检查目前的单元，并且添加相邻的单元到队列去
        rowNum = [-1, 0, 0, 1]
        colNum = [0, -1, 1, 0]
        for i in range(4):
            row = point_x + rowNum[i]
            col = point_y + colNum[i]
            opposite_x = point_x - rowNum[i]
            opposite_y = point_y - colNum[i]
            if row >= 0 and row < len(mesh) and col >= 0 and col < len(mesh[0]) and mesh[row][col] == 'o' and not (row, col) in visited:
                # 检查玩家是否能到达与目标点隔着箱子的对面的地点
                mesh2 = copy.deepcopy(mesh)
                mesh2[point_x][point_y] = "$"  # draw selected star in it's current position
                playerSteps = BFS(mesh2, (player_x, player_y), (opposite_x, opposite_y))
                if playerSteps != None:
                    # mark cell as visited and enqueue it
                    visited.add((row, col))
                    q.put(((row, col), distance + playerSteps + 1, (point_x, point_y)))
    return None  # 目的地无法到达


def BFS(mesh, src, dest):
    """广度优先搜索Breadth First Search，函数查找给定源单元到目标单元之间的最短路径。"""
    src_x, src_y = src
    dest_x, dest_y = dest
    if mesh[src_x][src_y] != 'o' or mesh[dest_x][dest_y] != 'o':
        return None
    visited = set()  # keep track of visited cells
    visited.add(src)  # Mark the source cell as visited
    q = queue.Queue()  # list to hold the calculated distance for each point to dest
    q.put((src, 0))  # 0 steps to reach src
    while not q.empty():  # Do a BFS starting from source cell
        (point_x, point_y), distance = q.get()
        # If we have reached the destination cell, we are done..
        if point_x == dest_x and point_y == dest_y: return distance
        # Check current cell and add neighboring cells to the queue
        rowNum = [-1, 0, 0, 1]
        colNum = [0, -1, 1, 0]
        for i in range(4):
            row = point_x + rowNum[i]
            col = point_y + colNum[i]
            if row >= 0 and row < len(mesh) and col >= 0 and col < len(mesh[0]) and mesh[row][col] == 'o' and not (row, col) in visited:
                # mark cell as visited and enqueue it
                visited.add((row, col))
                q.put(((row, col), distance + 1))
    return None  # 目的地无法到达


def isWall(mapObj, x, y):
    """Returns True if the (x, y) position on
    the map is a wall, otherwise return False."""
    if x < 0 or x >= len(mapObj) or y < 0 or y >= len(mapObj[x]):
        return False  # x and y aren't actually on the map.
    elif mapObj[x][y] in ('#', 'x'):
        return True  # wall is blocking
    return False


def decorateMap(mapObj, startxy):
    """Makes a copy of the given map object and modifies it.
        * Walls that are corners are turned into corner pieces.
     Here is what is done to it:
       * The outside/inside floor tile distinction is made.
        * Tree/rock decorations are randomly added to the outside tiles.

    Returns the decorated map object."""

    startx, starty = startxy  # 语法糖

    # 深度复制地图对象，这样我们就不用修改初始文件
    mapObjCopy = copy.deepcopy(mapObj)

    # 从地图数据移除所有非墙字符
    for x in range(len(mapObjCopy)):
        for y in range(len(mapObjCopy[0])):
            if mapObjCopy[x][y] in ('$', '.', '@', '+', '*'):
                mapObjCopy[x][y] = ' '

    # 泛洪填充算法决定内外地砖
    floodFill(mapObjCopy, startx, starty, ' ', 'o')

    # 假如墙的相邻两面邻接其他的墙，则把它转换为砖墙
    for x in range(len(mapObjCopy)):
        for y in range(len(mapObjCopy[0])):

            if mapObjCopy[x][y] == '#':
                if (isWall(mapObjCopy, x, y-1) and isWall(mapObjCopy, x+1, y)) or \
                   (isWall(mapObjCopy, x+1, y) and isWall(mapObjCopy, x, y+1)) or \
                   (isWall(mapObjCopy, x, y+1) and isWall(mapObjCopy, x-1, y)) or \
                   (isWall(mapObjCopy, x-1, y) and isWall(mapObjCopy, x, y-1)):
                    mapObjCopy[x][y] = 'x'

            elif mapObjCopy[x][y] == ' ' and random.randint(0, 99) < OUTSIDE_DECORATION_PCT:
                mapObjCopy[x][y] = random.choice(list(OUTSIDEDECOMAPPING.keys()))

    return mapObjCopy


def isBlocked(mapObj, gameStateObj, x, y):
    """Returns True if the (x, y) position on the map is
    blocked by a wall or star, otherwise return False."""

    if isWall(mapObj, x, y):
        return True

    elif x < 0 or x >= len(mapObj) or y < 0 or y >= len(mapObj[x]):
        return True

    elif (x, y) in gameStateObj['stars']:
        return True  # 一个箱子在在前面挡住了

    return False


def makeMove(mapObj, gameStateObj, playerMoveTo):
    """给定一张地图和游戏状态对象，看是否可能使玩家做到给定的移动，
    如果可以，改变玩家位置，并且改变玩家移动路径上可以被推动的箱子
    的位置。不行就算了

    如果玩家移动了，返回True,否则返回False"""

    # 确保玩家能以指定的路线移动
    playerx, playery = gameStateObj['player']

    # 语法糖，人们总是更容易记住一个单词而不是枯燥的坐标
    stars = gameStateObj['stars']

    # 按下移动玩家位置的方向键，更改玩家的坐标
    if playerMoveTo == UP:
        xOffset = 0
        yOffset = -1
    elif playerMoveTo == RIGHT:
        xOffset = 1
        yOffset = 0
    elif playerMoveTo == DOWN:
        xOffset = 0
        yOffset = 1
    elif playerMoveTo == LEFT:
        xOffset = -1
        yOffset = 0

    # 检查玩家是否能在指定的方向移动
    if isWall(mapObj, playerx + xOffset, playery + yOffset):
        return False
    else:
        if (playerx + xOffset, playery + yOffset) in stars:
            # 有一个箱子在路线上，看玩家是否能移动。
            if not isBlocked(mapObj, gameStateObj, playerx + (xOffset*2), playery + (yOffset*2)):
                # 移动箱子
                ind = stars.index((playerx + xOffset, playery + yOffset))
                stars[ind] = (stars[ind][0] + xOffset, stars[ind][1] + yOffset)
            else:
                return False
        # 移动玩家
        gameStateObj['player'] = (playerx + xOffset, playery + yOffset)
        return True


def helpScreen():
    """当点击帮助按钮时，出现帮助页面"""
    topCoord = 10
    instructionText = ['游戏简介',
                       ' ',
                       '经典的推箱子是一个来自日本的古老游戏，目的是在训练你的逻辑思考能力。',
                       '在一个狭小的仓库中，要求把木箱放到指定的位置,',
                       '稍不小心就会出现箱子无法移动或者通道被堵住的情况，所以需要巧妙的利用有限的空间和通道,',
                       '合理安排移动的次序和位置，才能顺利的完成任务。',

                       '推动所有箱子到目标位置。',
                       '箭头控制小人移动，WASD 控制镜头，P 更换角色。',
                       '按下 空格键 重玩本关，ESC 退 出 游 戏.',
                       '按下 N 键跳到下一关,    B 键返回上一关.', '',
                       '不仅如此:',
                       'CTRL+箭头 走五步, SHIFT+箭头 走到该行尽头,',
                       '按下 F: 切换全屏',
                       'CTRL+Z: 返回上一步']
    DISPLAYSURF.fill(BGCOLOR)
    # 定位 并且绘制文本
    for i in range(len(instructionText)):
        instSurf = BASICFONT.render(instructionText[i], 1, TEXTCOLOR, )
        instRect = instSurf.get_rect()
        topCoord += 10  # 每行之间用10个像素分割
        instRect.top = topCoord
        instRect.centerx = HALF_WINWIDTH
        topCoord += instRect.height  # 行高度适应.
        DISPLAYSURF.blit(instSurf, instRect)

    while True:  # 开始屏幕主循环
        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            elif event.type == VIDEORESIZE:
                set_window_size(event.dict['size'])
                startScreen()
                return
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    terminate()
                elif event.key == K_f:
                    set_window_size((settings.window_width, settings.window_height), not settings.fullscreen)
                    startScreen()
                    return
                # if event.key == pygame.K_AC_BACK:
                #    terminate()

                return
            elif event.type == pygame.MOUSEBUTTONUP:
                return  # 玩家按下一个键，返回

        # 调用display()方法，刷新页面，使设置生效
        pygame.display.update()
        FPSCLOCK.tick()  # 更新时钟


def startScreen():
    """展示开始游戏页面（开始业有标题和介绍）
    当玩家按下一个任意键，进入游戏"""

    # 标题图片的位置。
    titleRect = IMAGESDICT['title'].get_rect()
    topCoord = 10  # 定点坐标，定位文本位置
    titleRect.top = topCoord
    titleRect.centerx = HALF_WINWIDTH
    topCoord += titleRect.height

    # 备注，CTRL+SHIFT+Z之后再按下CTRL+Z，失效了
    instructionText = ['推动所有箱子到目标位置。',
                       '箭头控制小人移动，WASD 控制镜头，P 更换角色。',
                       '按下 空格键 重玩本关，ESC 退 出 游 戏.',
                       '按下 N 键跳到下一关,    B 键返回上一关.', '',
                       '不仅如此:',
                       'ALT+箭头: 小人一直走, CTRL 走五步, SHIFT 走到该行尽头,',
                       '点击鼠标: 去到任意一个符合规则的方块上, F: 切换全屏',
                       'CTRL+Z: 返回上一步']

    # 绘制黑色作为背景颜色：
    DISPLAYSURF.fill(STARTCREEN)

    # 把标题图片绘制到开始业：
    DISPLAYSURF.blit(IMAGESDICT['title'], titleRect)

    # 定位 并且绘制文本
    for i in range(len(instructionText)):
        instSurf = BASICFONT.render(instructionText[i], 1, TEXTCOLOR,)
        instRect = instSurf.get_rect()
        topCoord += 10  # 每行之间用10个像素分割
        instRect.top = topCoord
        instRect.centerx = HALF_WINWIDTH
        topCoord += instRect.height  # 行高度适应.
        DISPLAYSURF.blit(instSurf, instRect)

    while True:  # 开始屏幕主循环
        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()
            elif event.type == VIDEORESIZE:
                set_window_size(event.dict['size'])
                startScreen()
                return
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    terminate()
                elif event.key == K_f:
                    set_window_size((settings.window_width, settings.window_height), not settings.fullscreen)
                    startScreen()
                    return
                # if event.key == pygame.K_AC_BACK:
                #    terminate()

                return
            elif event.type == pygame.MOUSEBUTTONUP:
                return  # 玩家按下一个键，返回

        # 调用display()方法，刷新页面，使设置生效
        pygame.display.update()
        FPSCLOCK.tick()  # 更新时钟


def readLevelsFile(filename):
    assert os.path.exists(filename), 'Cannot find the level file: %s' % (filename)
    mapFile = open(filename, 'r')
    # 每个关卡以空白行结束
    content = mapFile.readlines() + ['\r\n']
    mapFile.close()

    levels = []  # 包含关卡对象的列表
    levelNum = 0
    mapTextLines = []  # 包含一个关卡地图的行
    mapObj = []  # the map object made from the data in mapTextLines
    for lineNum in range(len(content)):
        # 处理关卡文件的每行
        line = content[lineNum].rstrip('\r\n')

        if ';' in line:
            # 忽视 ; 行之后的内容
            line = line[:line.find(';')]

        if line != '':
            # 该行是地图的一部分
            mapTextLines.append(line)
        elif line == '' and len(mapTextLines) > 0:
            # 空白行标志文件关卡地图的结束
            # 把地图文本行(mapTextlines)转换为关卡对象

            # 找到地图文本最长的行
            maxWidth = -1
            for i in range(len(mapTextLines)):
                if len(mapTextLines[i]) > maxWidth:
                    maxWidth = len(mapTextLines[i])
            # 补充空格到最短行的末尾，
            # 这样能确保地图是矩形的
            for i in range(len(mapTextLines)):
                mapTextLines[i] += ' ' * (maxWidth - len(mapTextLines[i]))

            # 将地图文本行转换为地图对象
            for x in range(len(mapTextLines[0])):
                mapObj.append([])
            for y in range(len(mapTextLines)):
                for x in range(maxWidth):
                    mapObj[x].append(mapTextLines[y][x])

            # Loop through the spaces in the map and find the @, ., and $
            # characters for the starting game state.

            startx = None  # x和y是玩家的开始位置
            starty = None
            goals = []  # 目标位置元组
            stars = []  # 箱子位置列表
            for x in range(maxWidth):
                for y in range(len(mapObj[x])):
                    if mapObj[x][y] in ('@', '+'):
                        # '@' 是玩家, '+' 是玩家与目标
                        startx = x
                        starty = y
                    if mapObj[x][y] in ('.', '+', '*'):
                        # '.' 是目标, '*' 是箱子与目标
                        goals.append((x, y))
                    if mapObj[x][y] in ('$', '*'):
                        # '$' 代表星星
                        stars.append((x, y))

            # 基础关卡设置健全性检查:
            assert startx != None and starty != None, 'Level %s (around line %s) in %s is missing a "@" or "+" to mark the start point.' % (levelNum+1, lineNum, filename)
            assert len(goals) > 0, 'Level %s (around line %s) in %s must have at least one goal.' % (levelNum+1, lineNum, filename)
            assert len(stars) >= len(goals), 'Level %s (around line %s) in %s is impossible to solve. It has %s goals but only %s stars.' % (levelNum+1, lineNum, filename, len(goals), len(stars))

            # 创建关卡对象和开始游戏状态对象
            gameStateObj = {'player': (startx, starty),
                            'stepCounter': 0,
                            'stars': stars, GameStateItem.SELECTED_STAR_INDEX.name: None}
            levelObj = {'width': maxWidth,
                        'height': len(mapObj),
                        'mapObj': mapObj,
                        'goals': goals,
                        'startState': gameStateObj}

            levels.append(levelObj)

            # 重置变量以读取下一张地图
            mapTextLines = []
            mapObj = []
            gameStateObj = {}
            levelNum += 1
    return levels


def floodFill(mapObj, x, y, oldCharacter, newCharacter):
    """将旧值转换为新值，用来适应关卡对象。"""

    if mapObj[x][y] == oldCharacter:
        mapObj[x][y] = newCharacter

    if x < len(mapObj) - 1 and mapObj[x+1][y] == oldCharacter:
        floodFill(mapObj, x+1, y, oldCharacter, newCharacter)  # call right
    if x > 0 and mapObj[x-1][y] == oldCharacter:
        floodFill(mapObj, x-1, y, oldCharacter, newCharacter)  # call left
    if y < len(mapObj[x]) - 1 and mapObj[x][y+1] == oldCharacter:
        floodFill(mapObj, x, y+1, oldCharacter, newCharacter)  # call down
    if y > 0 and mapObj[x][y-1] == oldCharacter:
        floodFill(mapObj, x, y-1, oldCharacter, newCharacter)  # call up


def drawMap(mapObj, gameStateObj, goals):
    """绘制地址到surface对象，包括玩家和星星，该函数不调用pygame.display.update()函数"""

    mapSurfWidth = len(mapObj) * TILEWIDTH
    mapSurfHeight = (len(mapObj[0]) - 1) * TILEFLOORHEIGHT + TILEHEIGHT
    mapSurf = pygame.Surface((mapSurfWidth, mapSurfHeight))
    mapSurf.fill(BGCOLOR)  # 以纯色背景开始.

    selectedStar = None
    if gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name] != None:
        selectedStar = gameStateObj['stars'][gameStateObj[GameStateItem.SELECTED_STAR_INDEX.name]]

    # 绘制地砖精灵在surface上
    for x in range(len(mapObj)):
        for y in range(len(mapObj[x])):
            spaceRect = pygame.Rect((x * TILEWIDTH, y * TILEFLOORHEIGHT, TILEWIDTH, TILEHEIGHT))
            if mapObj[x][y] in TILEMAPPING:
                baseTile = TILEMAPPING[mapObj[x][y]]
            elif mapObj[x][y] in OUTSIDEDECOMAPPING:
                baseTile = TILEMAPPING[' ']

            # 首先绘制地砖
            mapSurf.blit(baseTile, spaceRect)

            if mapObj[x][y] in OUTSIDEDECOMAPPING:
                # Draw any tree/rock decorations that are on this tile.
                mapSurf.blit(OUTSIDEDECOMAPPING[mapObj[x][y]], spaceRect)
            elif (x, y) in gameStateObj['stars']:
                if (x, y) in goals:
                    # A goal AND star are on this space, draw goal first.
                    mapSurf.blit(IMAGESDICT['covered goal'], spaceRect)
                # Then draw the star sprite.
                if selectedStar != None and (x, y) == selectedStar:
                    mapSurf.blit(IMAGESDICT['star red'], spaceRect)
                else:
                    mapSurf.blit(IMAGESDICT['star'], spaceRect)
            elif (x, y) in goals:
                # Draw a goal without a star on it.
                mapSurf.blit(IMAGESDICT['uncovered goal'], spaceRect)

            # 最后绘制地砖上的小人
            if (x, y) == gameStateObj['player']:
                # Note: The value "currentImage" refers
                # to a key in "PLAYERIMAGES" which has the
                # specific player image we want to show.
                mapSurf.blit(PLAYERIMAGES[currentImage], spaceRect)

    return mapSurf


def isLevelFinished(levelObj, gameStateObj):
    """Returns True if all the goals have stars in them."""
    for goal in levelObj['goals']:
        if goal not in gameStateObj['stars']:
            return False  # Found a space with a goal but no star on it.
    return True


def terminate():
    settings.save()
    try:
        with open('gameStateObj.pkl', 'wb') as f:
            pickle.dump(gameStateObj, f, pickle.HIGHEST_PROTOCOL)
    except Exception as e: print("Error saving gameStateObj: {}".format(str(e)))
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
