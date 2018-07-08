#!/usr/bin/env python
import cv
import time
import numpy
import pygame
import random
import threading
import traceback

CAMERA_SIZE = (640, 480)
WINDOW_SIZE = (800, 600)

BACKGROUND = (255, 255, 255)
COLORS = [(255, 0, 0), (0, 0, 255)]
THRESHOLD = 320

AMOUNT = 1000
IMAGE = 8
SPEED = [1, 30]
TIME = 100

def convert(image):
    image_size = image.get_size()
    color = [False for i in range(len(COLORS))]

    for i in range(image_size[0]):
        for j in range(image_size[1]):
            pixel = image.get_at((i, j))
            for k in range(len(COLORS)):
                if sum([abs(COLORS[k][l] - pixel[l]) for l in range(3)]) < THRESHOLD:
                    image.set_at((i, j), COLORS[k])
                    color[k] = True
                    break
            if image.get_at((i, j)) == pixel:
                image.set_at((i, j), BACKGROUND)

    return sum(color)

class Tux(pygame.sprite.Sprite):
    def __init__(self, position, window_size, field):
        pygame.sprite.Sprite.__init__(self)
        self.window_size = window_size
        self.field = field

        self.left_image = []
        self.right_image = []
        for i in range(IMAGE):
            self.left_image.append(pygame.image.load('smalltux-left-%d.png' % (i + 1)).convert_alpha())
            self.right_image.append(pygame.image.load('smalltux-right-%d.png' % (i + 1)).convert_alpha())

        self.image_index = 0
        self.image = self.right_image[self.image_index]
        self.rect = pygame.Rect((0, 0), self.image.get_size())
        self.rect.center = position

        self.accel = [0, 0]
        self.speed = [0, 0]
        self.on_floor = True

    def update(self):
        pressed_keys = pygame.key.get_pressed()

        self.image_index += 1
        if self.image_index == IMAGE:
            self.image_index = 0

        if pressed_keys[pygame.K_RIGHT]:
            self.image = self.right_image[self.image_index]
            self.accel[0] = SPEED[0]
        elif pressed_keys[pygame.K_LEFT]:
            self.image = self.left_image[self.image_index]
            self.accel[0] = -SPEED[0]
        else:
            self.accel[0] = 0

        if pressed_keys[pygame.K_UP] and self.on_floor:
                self.accel[1] = -SPEED[1]
                self.on_floor = False
        else:
            self.accel[1] = 0

        for i in range(2):
            self.speed[i] += self.accel[i]

        self.rect.x += self.speed[0]
        self.rect.y += self.speed[1]

        if self.rect.left < 0:
            self.rect.left = 0
            self.accel[0] = 0
            self.speed[0] = 0
        elif self.rect.right > CAMERA_SIZE[0]:
            self.rect.right = CAMERA_SIZE[0]
            self.accel[0] = 0
            self.speed[0] = 0

        if self.rect.top < 0:
            self.rect.top = 0
            self.accel[1] = 0
            self.speed[1] = 0

        if self.speed[0] > 0:
            self.speed[0] -= SPEED[0] * 0.5
        elif self.speed[0] < 0:
            self.speed[0] += SPEED[0] * 0.5

        if not self.on_floor:
            self.speed[1] += SPEED[1] * 0.1
        if self.rect.bottom > CAMERA_SIZE[1]:
            self.rect.bottom = CAMERA_SIZE[1]
            self.speed[1] = 0
            self.on_floor = True

    def draw(self, screen):
        x = (self.window_size[0] - CAMERA_SIZE[0]) / 2 + self.rect.left
        y = (self.window_size[1] - CAMERA_SIZE[1]) / 2 + self.rect.top
        screen.blit(self.image, (x, y))

class Game(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        pygame.init()
        self.window_size = pygame.display.list_modes()[0]
        #self.screen = pygame.display.set_mode(self.window_size, pygame.FULLSCREEN)
        self.screen = pygame.display.set_mode(self.window_size)

        self.cap = cv.CaptureFromCAM(-1)
        cv.SetCaptureProperty(self.cap, cv.CV_CAP_PROP_FRAME_WIDTH, CAMERA_SIZE[0])
        cv.SetCaptureProperty(self.cap, cv.CV_CAP_PROP_FRAME_HEIGHT, CAMERA_SIZE[1])

        self.correction = [[0, 0], [0, 0], [0, 0], [0, 0]]
        self.field = None
        self.mode = 0
        self.points = []
        self.transform = None
        self.running = True

    def capture(self, transform = None):
        query_img = cv.QueryFrame(self.cap)
        camera_img = cv.CreateMat(CAMERA_SIZE[1], CAMERA_SIZE[0], cv.CV_8UC3)
        cv.CvtColor(query_img, camera_img, cv.CV_BGR2RGB)

        if transform:
            transform_img = cv.CreateMat(CAMERA_SIZE[1], CAMERA_SIZE[0], cv.CV_8UC3)
            cv.WarpPerspective(camera_img, transform_img, transform)
            img = pygame.image.fromstring(transform_img.tostring(), CAMERA_SIZE, 'RGB')
        else:
            img = pygame.image.fromstring(camera_img.tostring(), CAMERA_SIZE, 'RGB')

        return img

    def calc_transform(self, points, correction):
        src = [(0, 0), (0, 0), (0, 0), (0, 0)] 
        dst = [(0, 0), (0, CAMERA_SIZE[1]), (CAMERA_SIZE[0], 0), CAMERA_SIZE]

        for i in range(4):
            minimum = sum([j ** 2 for j in CAMERA_SIZE])
            for j in range(4):
                distance = sum([(dst[i][k] - points[j][k]) ** 2 for k in range(2)])
                if distance < minimum:
                    minimum = distance
                    src[i] = tuple([points[j][k] + correction[i][k] for k in range(2)])
        
        transform = cv.CreateMat(3, 3, cv.CV_32FC1)
        cv.GetPerspectiveTransform(src, dst, transform)
        return transform

    def event(self):
        selection = 0

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    if self.mode == 1:
                        if event.key == pygame.K_UP:
                            self.correction[selection][0] += 1
                        elif event.key == pygame.K_DOWN:
                            self.correction[selection][0] -= 1
                        elif event.key == pygame.K_LEFT:
                            self.correction[selection][1] += 1
                        elif event.key == pygame.K_RIGHT:
                            self.correction[selection][1] -= 1
                        elif event.key == pygame.K_0:
                            selection = 0
                        elif event.key == pygame.K_1:
                            selection = 1
                        elif event.key == pygame.K_2:
                            selection = 2
                        elif event.key == pygame.K_3:
                            selection = 3
                        self.transform = self.calc_transform(self.points, self.correction)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.mode == 0:
                            self.points.append(tuple([(event.pos[i] - (self.window_size[i] - CAMERA_SIZE[i]) / 2) for i in range(2)]))
                            if len(self.points) == 4:
                                self.transform = self.calc_transform(self.points, self.correction)
                                self.mode = 1
                        elif self.mode == 1:
                            self.mode = 2
                        elif self.mode == 2:
                            self.field = None
                            self.mode = 3
                        elif self.mode == 3:
                            self.mode = 2
                    if event.button == 3:
                        if self.mode == 0 or self.mode == 1 or self.mode == 2:
                            self.points = []
                            self.mode = 0

    def run(self):
        event = threading.Thread(target = self.event)
        event.start()

        while self.running:
            self.screen.fill((255, 255, 255))

            if self.mode == 0: # Calibration
                img = self.capture()
                self.screen.blit(img, tuple([(self.window_size[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]))
                for point in self.points:
                    pygame.draw.circle(self.screen, (255, 0, 0), tuple([point[i] + (self.window_size[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]), 10)
            elif self.mode == 1: # Change calibration
                img = self.capture(self.transform)
                self.screen.blit(img, tuple([(self.window_size[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]))
            elif self.mode == 2: # Set field
                img = self.capture(self.transform)
                self.screen.blit(img, tuple([(self.window_size[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]))
            elif self.mode == 3: # Game
                if not self.field:
                    self.field = self.capture(self.transform)
                    color = convert(self.field)
                    self.tux = Tux((0, 0), self.window_size, self.field)
                self.screen.blit(self.field, tuple([(self.window_size[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]))
                self.tux.update()
                self.tux.draw(self.screen)

            pygame.display.update()
            time.sleep(0.01)

        del(self.cap)

if __name__ == '__main__':
    main = Game()
    main.start()
