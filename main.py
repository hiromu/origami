#!/usr/bin/env python
import cv
import time
import pygame
import random

CAMERA_SIZE = (640, 480)
WINDOW_SIZE = (800, 600)

BACKGROUND = (255, 255, 255)
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (128, 128, 0), (128, 0, 128), (0, 128, 128)]
SAND = (0, 0, 0)
THRESHOLD = 50

AMOUNT = 1000
SPEED = 10
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

if __name__ == '__main__':
    pygame.init()
    WINDOW_SIZE = pygame.display.list_modes()[0]
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.FULLSCREEN)

    cap = cv.CaptureFromCAM(-1)
    cv.SetCaptureProperty(cap, cv.CV_CAP_PROP_FRAME_WIDTH, CAMERA_SIZE[0])
    cv.SetCaptureProperty(cap, cv.CV_CAP_PROP_FRAME_HEIGHT, CAMERA_SIZE[1])
    camera_img = cv.CreateMat(CAMERA_SIZE[1], CAMERA_SIZE[0], cv.CV_8UC3)
    transform_img = cv.CreateMat(CAMERA_SIZE[1], CAMERA_SIZE[0], cv.CV_8UC3)

    color = 0
    field = None
    mode = 0
    points = []
    timer = 0
    transform = cv.CreateMat(3, 3, cv.CV_32FC1)

    while True:
        screen.fill((255, 255, 255))

        if mode == 0: # Calibration
            query_img = cv.QueryFrame(cap)
            cv.CvtColor(query_img, camera_img, cv.CV_BGR2RGB)
            img = pygame.image.fromstring(camera_img.tostring(), CAMERA_SIZE, 'RGB')
            screen.blit(img, tuple([(WINDOW_SIZE[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]))
            for point in points:
                pygame.draw.circle(screen, (255, 0, 0), tuple([point[i] + (WINDOW_SIZE[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]), 5)
        elif mode == 1: # Set field
            query_img = cv.QueryFrame(cap)
            cv.CvtColor(query_img, camera_img, cv.CV_BGR2RGB)
            cv.WarpPerspective(camera_img, transform_img, transform)
            img = pygame.image.fromstring(transform_img.tostring(), CAMERA_SIZE, 'RGB')
            screen.blit(img, tuple([(WINDOW_SIZE[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]))
        elif mode == 2: # Game
            if not field:
                query_img = cv.QueryFrame(cap)
                cv.CvtColor(query_img, camera_img, cv.CV_BGR2RGB)
                cv.WarpPerspective(camera_img, transform_img, transform)
                field = pygame.image.fromstring(transform_img.tostring(), CAMERA_SIZE, 'RGB')
                color = convert(field)

            if timer < TIME:
                for i in range(AMOUNT):
                    (x, y) = (random.randint(0, field.get_width() - 1), random.randint(0, field.get_height() / 4))
                    if field.get_at((x, y)) == BACKGROUND:
                        field.set_at((x, y), SAND)

            for i in range(field.get_width()):
                for j in range(field.get_height()):
                    if random.randint(0, 10) < 8:
                        pixel = field.get_at((i, j))
                        if pixel == SAND:
                            for k in range(1, SPEED):
                                if j + k < field.get_height():
                                    lower = field.get_at((i, j + k))
                                    if lower != BACKGROUND and lower != SAND:
                                        break
                                else:
                                    break
                            if k > 1:
                                field.set_at((i, j), field.get_at((i, j + k - 1)))
                                field.set_at((i, j + k - 1), pixel)
                    if random.randint(0, 10) < 8:
                        pixel = field.get_at((i, j))
                        if pixel == SAND:
                            if random.randint(0, 1):
                                for k in range(1, random.randint(2, 5)):
                                    if i + k < field.get_width():
                                        horizon = field.get_at((i + k, j))
                                        if horizon != BACKGROUND and horizon != SAND:
                                            break
                                    else:
                                        break
                                if k > 1:
                                    field.set_at((i, j), field.get_at((i + k - 1, j)))
                                    field.set_at((i + k - 1, j), pixel)
                            else:
                                for k in range(1, random.randint(2, 5)):
                                    if 0 <= i - k:
                                        horizon = field.get_at((i - k, j))
                                        if horizon != BACKGROUND and horizon != SAND:
                                            break
                                    else:
                                        break
                                if k > 1:
                                    field.set_at((i, j), field.get_at((i - k + 1, j)))
                                    field.set_at((i - k + 1, j), pixel)
                            
            screen.blit(field, tuple([(WINDOW_SIZE[i] - CAMERA_SIZE[i]) / 2 for i in range(2)]))

        for event in pygame.event.get():
            finish = False

            if event.type == pygame.QUIT:
                finish = True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    finish = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if mode == 0:
                        points.append(tuple([(event.pos[i] - (WINDOW_SIZE[i] - CAMERA_SIZE[i]) / 2) for i in range(2)]))
                        if len(points) == 4:
                            points.sort()
                            cv.GetPerspectiveTransform(points, [(0, 0), (0, CAMERA_SIZE[1]), (CAMERA_SIZE[0], 0), CAMERA_SIZE], transform)
                            mode = 1
                    elif mode == 1:
                        field = None
                        timer = 0
                        mode = 2
                    elif mode == 2:
                        mode = 1
                if event.button == 3:
                    if mode == 0 or mode == 1:
                        points = []
                        mode = 0

            if finish:
                del(cap)
                exit()

        pygame.display.update()
        time.sleep(0.001)
