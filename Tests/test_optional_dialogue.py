# Tests mandatory Dialogue
import os
import pstats
import cProfile

import pygame
import pyautogui


import Code.GlobalConstants as GC
import Code.SaveLoad as SaveLoad
import Code.GameStateObj as GameStateObj
import Code.Dialogue as Dialogue
import Code.Engine as Engine

import logging

pyautogui.PAUSE = 0
GC.DISPLAYSURF = pygame.display.set_mode((GC.WINWIDTH, GC.WINHEIGHT))

my_level = logging.DEBUG
logging.basicConfig(filename='Tests/debug.log.test', filemode='w', level=my_level,
                    disable_existing_loggers=False, format='%(levelname)8s:%(module)20s: %(message)s')

def main():
    gameStateObj = GameStateObj.GameStateObj()
    metaDataObj = {}
    gameStateObj.build_new()
    gameStateObj.set_generic_mode()
    scripts = ['base', 'village', 'unlock', 'switch', 'talk', 'search']
    num = 0
    while True:
        levelfolder = 'Data/Level' + str(num)
        if not os.path.exists(levelfolder):
            break
        print('Level: %s' % num)
        SaveLoad.load_level(levelfolder, gameStateObj, metaDataObj)
        print('Num Units: %s  Map Size: %s' % (len(gameStateObj.allunits), gameStateObj.map.width*gameStateObj.map.height))
        if num >= 0:
            for script in scripts:
                fp = levelfolder + '/' + script + 'Script.txt'
                run(gameStateObj, metaDataObj, fp)
        gameStateObj.clean_up()
        print('Num Units Remaining: %s'%(len(gameStateObj.allunits)))
        num += 1

def run(gameStateObj, metaDataObj, fp):
    if os.path.exists(fp):
        print(fp)
        gameStateObj.message.append(Dialogue.Dialogue_Scene(fp, unit=gameStateObj.allunits[0], if_flag=True))
        gameStateObj.stateMachine.changeState('dialogue')
        counter = 0
        while gameStateObj.message:
            Engine.update_time()
            counter += 1
            if not counter%50:
                pyautogui.press('x')
            eventList = Engine.build_event_list()
            mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
            while repeat:
                mapSurf, repeat = gameStateObj.stateMachine.update(eventList, gameStateObj, metaDataObj)
            GC.DISPLAYSURF.blit(mapSurf, (0, 0))
            pygame.display.update()

if __name__ == '__main__':
    cProfile.run("main()", "Profile.prof")
    s = pstats.Stats("Profile.prof")
    s.strip_dirs().sort_stats("time").print_stats(20)
    os.remove("Profile.prof")
