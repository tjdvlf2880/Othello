from contextlib import closing
from io import StringIO
from os import path
from typing import Optional
import numpy as np
import asyncio


import gymnasium as gym
from gymnasium import Env, spaces
from gymnasium.envs.toy_text.utils import categorical_sample
from gymnasium.error import DependencyNotInstalled

try:
    import pygame
except ImportError as e:
    raise DependencyNotInstalled(
        'pygame is not installed'
    ) from e

class OthelloEnv(gym.Env):
    """

    ## Description
    The game of Othello starts with black making the first move on an 8x8 grid. If neither player can make a move, the game ends.

    ## Action Space
    The action space consists of all valid positions on the 8x8 grid where a move would flip at least one opponent's disc.
    As Othello is not stochastic, the transition probability always 1.0.

    ## Observation Space
    The observation space is the current state of the 8x8 grid, showing the positions of all black and white discs.
    The State is turn-based.
    
    BoardState is represeted using the following keys:
    empty : 0
    black : 1
    white : 2

    ## Starting State
    Two black discs are placed on (4, 5) and (5, 4), corresponding to indices 27 and 36 in 1D array.
    Two white discs are placed on (4, 4) and (5, 5), corresponding to indices 28 and 35 in 1D array.

    Black turn first.

    ## Reward
    
    ## Information
    step() and reset() function return a dict with the following keys:
    - turn  : returns b,w 
    - autoplay :  If autoplay is false, input will be given by user interaction

    ## metadata
    In metadata, you can set the following keys:
    autoplay 
    render_fps :if autoplay is auto, it simulates automatically with this fps value"

    """

    metadata = {
        "render_modes": "human",
        "render_fps": 30,
        'autoplay': False # press p
    }
    def __init__(self, render_mode: Optional[str] = None):
        self.metadata['render_modes'] = render_mode
        # pygame utils
        self.cell_size = 60
        self.window_size = (
            self.cell_size*8, 
            self.cell_size*(8+2) # +2 cells for showing score
        )
        self.observation_space = spaces.MultiDiscrete([3] * 64)
        self.action_space = spaces.Discrete(8*8)
        self.boardImg = None
        self.whiteImg = None
        self.blackImg = None
        self.selectImg = None
        self.window_surface = None
        self.clock = None

    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)
        self.board = np.zeros(8*8, dtype=int)
        self.board[27] = 1
        self.board[36] = 1
        self.board[28] = 2
        self.board[35] = 2
        self.Curplayer = 1
        self.done = False
        self.blackSum = 2
        self.whiteSum = 2

        if self.metadata['render_modes'] == "human":
            self._init_render_gui()
        self.render()
        return ( self.board, 0, False , False, {'autoplay': self.metadata['autoplay'], 'turn':self.Curplayer} )
    
    def render(self):
        if self.metadata['render_modes'] == "human":
            return self._render_gui()


    def _init_render_gui(self):
        if self.window_surface is None:
            pygame.init()
            pygame.display.init()
            pygame.display.set_caption("Othello")
            self.window_surface = pygame.display.set_mode(self.window_size)
        self.font = pygame.font.Font(None, 36)
        self.MouseX , self.MouseY = 0,0
        if self.clock is None:
            self.clock = pygame.time.Clock()
        if self.boardImg is None:
            self.boardImg = pygame.transform.scale(pygame.image.load(path.join(path.dirname(__file__), "img/board.png")), (self.cell_size*8,self.cell_size*8))
        if self.whiteImg is None:
            self.whiteImg = pygame.transform.scale(pygame.image.load(path.join(path.dirname(__file__), "img/white.png")), (self.cell_size,self.cell_size))
        if self.blackImg is None:
            self.blackImg = pygame.transform.scale(pygame.image.load(path.join(path.dirname(__file__), "img/black.png")), (self.cell_size,self.cell_size))
        if self.selectImg is None:
            self.selectImg = pygame.transform.scale(pygame.image.load(path.join(path.dirname(__file__), "img/select.png")), (self.cell_size,self.cell_size))

    def _render_gui(self):
        self.window_surface.fill((0, 0, 0))
        self.clock.tick(self.metadata["render_fps"])
        self.window_surface.blit(self.boardImg, (0,0))
        for i, v in enumerate(self.board):
            if(v !=0 ):
                row, col = np.unravel_index(i, (8,8))
                pos = (col * self.cell_size, row * self.cell_size)
                if(v==1):
                    self.window_surface.blit(self.blackImg, pos)
                else:
                    self.window_surface.blit(self.whiteImg, pos)

        self._render_text(f"Turn : {self.Curplayer}",self.cell_size*8//2, self.cell_size*9-30)
        self._render_text(f"B/W : {self.blackSum}/{self.whiteSum}",self.cell_size*8//2, self.cell_size*9)

        if(not self.metadata['autoplay']):
            row  = self.MouseY//self.cell_size
            col  = self.MouseX//self.cell_size
            a = 8*row+col
            if self.is_valid_action(a):
                pos = (col * self.cell_size, row * self.cell_size)
                self.window_surface.blit(self.selectImg, pos)
 
        pygame.event.pump()
        pygame.display.update()
                    
    def _render_text(self , text, x,y):
        text_surface = self.font.render(text, True, (255, 255, 255))
        self.window_surface.blit(text_surface, (x - text_surface.get_width() // 2, y - text_surface.get_height() // 2))

    def _check_coordinates(self, pos):
        if( 0< pos <8 *self.cell_size ):
            return True

    def close(self):
        self.coroutine.cancel()
        pygame.quit()
        return super().close()

    def is_valid_action(self, a):
        # 주어진 위치에 돌을 둘 수 있는지 확인하는 함수
        if not ( 0<= a < 8* 8):
            return False
        if self.board[a] != 0:
            return False  # 이미 돌이 있는 위치에는 둘 수 없음
        # 상하좌우 및 대각선 방향에 적군 돌이 있는지 확인
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
        row, col = np.unravel_index(a, (8,8))
        for dr, dc in directions:
            r, c = row + dr, col + dc
            find = False
            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[ 8*r+c] == 0:
                    break
                elif self.board[ 8*r+c] != self.Curplayer:
                    r, c = r + dr, c + dc
                    find =  True 
                else:
                    if(find):
                        return True
                    else:
                        break

        return False
    


    def capture_action(self, a):
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]
        row, col = np.unravel_index(a, (8,8))
        for dr, dc in directions:
            r, c = row + dr, col + dc
            find = False
            while 0 <= r < 8 and 0 <= c < 8:
                if self.board[ 8*r+c] == 0:
                    break
                elif self.board[ 8*r+c] != self.Curplayer:
                    r, c = r + dr, c + dc
                    find =  True 
                else:
                    if(find):
                        r, c = r - dr, c - dc
                        while ( r, c ) != (row, col):
                            self.board[8*r+c] = self.Curplayer
                            if(self.Curplayer == 1):
                                self.blackSum +=1
                                self.whiteSum -=1
                            else:
                                self.blackSum -=1
                                self.whiteSum +=1
                            r, c = r - dr, c - dc
                        break
                    else:
                        break
    def step(self, a):
        if(not self.metadata['autoplay']):
            while True:
                pygame.event.pump()
                pygame.display.update()
                self.MouseX , self.MouseY = pygame.mouse.get_pos()
                self.render()
                if(pygame.mouse.get_pressed()[0]):
                    row  = self.MouseY//self.cell_size
                    col  = self.MouseX//self.cell_size
                    a = 8*row+col
                    if self.is_valid_action(a):
                        break

        # 움직일 수 있는 돌 위치를 체크하여 반환하고, 
        # 가치 함수를 지정해 반환하고
        # 게임 종료 조건을 만들어야 한다.


        blackSumold = self.blackSum
        whiteumold = self.whiteSum
        self.capture_action(a)
        if(self.Curplayer == 1):
            if(blackSumold != self.blackSum):
                self.board[a] = self.Curplayer
                self.blackSum +=1     
        else:
            if(whiteumold != self.whiteSum):
                self.board[a] = self.Curplayer
                self.whiteSum +=1     

        player = self.Curplayer
        if( self.Curplayer == 1) :
            self.Curplayer = 2
        else:
            self.Curplayer = 1
        return ( self.board, 0, False , False, {'autoplay': self.metadata['autoplay'], 'turn':player} )