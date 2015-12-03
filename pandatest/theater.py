#!/usr/bin/env python

"""
Author: Josh Enes
Last Updated: 2015-03-13

This is a demo of Panda's portal-culling system. It demonstrates loading
portals from an EGG file, and shows an example method of selecting the
current cell using geoms and a collision ray.
"""

# Some config options which can be changed.
ENABLE_PORTALS = False # Set False to disable portal culling and see FPS drop!
DEBUG_PORTALS = False # Set True to see visually which portals are used

# Load PRC data
from panda3d.core import loadPrcFileData
if ENABLE_PORTALS:
    loadPrcFileData('', 'allow-portal-cull true')
    if DEBUG_PORTALS:
        loadPrcFileData('', 'debug-portal-cull true')
loadPrcFileData('', 'window-title Portal Demo')
loadPrcFileData('', 'sync-video false')
loadPrcFileData('', 'show-frame-rate-meter true')
loadPrcFileData('', 'texture-minfilter linear-mipmap-linear')

# Import needed modules
import random, math
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.actor.Actor import Actor
from panda3d.core import PerspectiveLens, NodePath, LVector3, LPoint3, \
    TexGenAttrib, TextureStage, TransparencyAttrib, CollisionTraverser, \
    CollisionHandlerQueue, TextNode, CollisionRay, CollisionNode, AmbientLight, \
    DirectionalLight

import lightarm
servos = lightarm.Servos(lightarm.ServosPath)

def add_instructions(pos, msg):
    """Function to put instructions on the screen."""
    return OnscreenText(text=msg, style=1, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
                        parent=base.a2dTopLeft, align=TextNode.ALeft,
                        pos=(0.08, -pos - 0.04), scale=.05)

def add_title(text):
    """Function to put title on the screen."""
    return OnscreenText(text=text, style=1, pos=(-0.1, 0.09), scale=.08,
                        parent=base.a2dBottomRight, align=TextNode.ARight,
                        fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1))

def clamp1(x): return min(1, max(-1, x))


class Game(ShowBase):
    """Sets up the game, camera, controls, and loads models."""
    def __init__(self):
        ShowBase.__init__(self)

        self.dirTypes = ['heading', 'pitch', 'roll']
        self.dirType = 0

        # Display instructions
        add_title("Panda3D Tutorial: Portal Culling")
        add_instructions(0.06, "[Esc]: Quit")
        self.posText = add_instructions(0.12, "pos")
        self.anglesText = add_instructions(0.18, "angle")
        self.armHprText = add_instructions(0.24, "hpr")
        self.dirText = add_instructions(.30, self.dirTypes[0])
        self.forearmText = add_instructions(0.36, "angle")
        self.baseText = add_instructions(0.42, "angle")
        """add_instructions(0.12, "[W]: Move Forward")
        add_instructions(0.18, "[A]: Move Left")
        add_instructions(0.24, "[S]: Move Right")
        add_instructions(0.30, "[D]: Move Back")
        add_instructions(0.36, "Arrow Keys: Look Around")
        add_instructions(0.42, "[F]: Toggle Wireframe")
        add_instructions(0.48, "[X]: Toggle X-Ray Mode")
        add_instructions(0.54, "[B]: Toggle Bounding Volumes")"""

        # Setup controls
        self.keys = {}
        for key in ['arrow_left', 'arrow_right', 'arrow_up', 'arrow_down',
                    'a', 'd', 'w', 's', 'q', 'e']:
            self.keys[key] = 0
            self.accept(key, self.push_key, [key, 1])
            self.accept('shift-%s' % key, self.push_key, [key, 1])
            self.accept('%s-up' % key, self.push_key, [key, 0])

        self.accept("b", self.push_key, ["Rleft", True])
        self.accept("b-up", self.push_key, ["Rleft", False])
        self.accept("n", self.push_key, ["Rright", True])
        self.accept("n-up", self.push_key, ["Rright", False])
        self.accept("h", self.push_key, ["Rforward", True])
        self.accept("h-up", self.push_key, ["Rforward", False])
        self.keys['Rleft'] = self.keys['Rright'] = self.keys['Rforward'] = 0

        self.accept('escape', self.exitButton)
        self.accept('p', self.selectDir)
        self.accept('[', self.incDir, [-15])
        self.accept(']', self.incDir, [15])
        #self.disableMouse()

        # Setup camera
        lens = PerspectiveLens()
        lens.setFov(60)
        lens.setNear(0.01)
        lens.setFar(1000.0)
        self.cam.node().setLens(lens)
        self.camera.setPos(-50, 0, 0)
        self.pitch = 0.0
        self.heading = 0
        
        ambientLight = AmbientLight("ambientLight")
        ambientLight.setColor((.3, .3, .3, 1))
        directionalLight = DirectionalLight("directionalLight")
        directionalLight.setDirection((-5, -5, -5))
        directionalLight.setColor((1, 1, 1, 1))
        directionalLight.setSpecularColor((1, 1, 1, 1))
        render.setLight(render.attachNewNode(ambientLight))
        render.setLight(render.attachNewNode(directionalLight))

        # Load level geometry
        self.level = self.loader.loadModel('models/theater')
        self.level.reparentTo(self.render)

        self.isMoving = False
        self.ralph = Actor("models/ralph",
                           {"run": "models/ralph-run",
                            "walk": "models/ralph-walk"})
        self.ralph.reparentTo(render)
        self.ralph.setScale(.2)


        self.arms = []
        idMap = {0:9, 1:11, 2:29, 3:31, 4:15}

        for node in self.level.get_children():
          if not node.getName().startswith('arm'): continue
          arm = Actor("models/robotarm")
          self.arms.append(arm)
          arm.reparentTo(render)
          arm.setName(node.getName())
          arm.setPos(node.getPos())
          arm.setHpr(node.getHpr())
          #arm.setScale(.2)

          tokens = node.getName().split('.')
          try: id = int(tokens[1])
          except: id = 0
          arm.baseID = idMap[id]

          arm.jointForearm = arm.controlJoint(None, "modelRoot", "forearm")
          arm.jointBase = arm.controlJoint(None, "modelRoot", "base")
          print node.getName(), str(node.getPos()), str(node.getHpr())
   
        taskMgr.add(self.printLoc, "printLoc")
        taskMgr.add(self.monitorArms, "robot arms")
        self.taskMgr.add(self.update, 'main loop')

    def incDir(self, inc):
      if self.dirType == 0: self.arms[0].setH(self.arms[0].getH() + inc)
      elif self.dirType == 1: self.arms[0].setP(self.arms[0].getP() + inc)
      elif self.dirType == 2: self.arms[0].setR(self.arms[0].getR() + inc)

    def selectDir(self):
      self.dirType = (self.dirType + 1) % len(self.dirTypes)
      self.dirText.setText(self.dirTypes[self.dirType])

    def exitButton(self):
      #import pdb; pdb.set_trace()
      servos.exit()
      __import__('sys').exit()

    def printLoc(self, task):
      self.posText.setText(str(self.camera.getPos())) 
      self.anglesText.setText(str(self.camera.getHpr()))
      self.armHprText.setText(str(self.arms[0].getHpr()))
      self.baseText.setText('base HPR: ' + str(self.arms[0].jointBase.getHpr()))
      self.forearmText.setText('forearm HPR: ' + str(self.arms[0].jointForearm.getHpr()))
      return task.again

    def monitorArms(self, task):
      #import pdb; pdb.set_trace()
      for arm in self.arms:
        direction = self.ralph.get_pos() - arm.get_pos()
        direction.normalize()
        #print(direction)

        # camera starts facing along x
        dec = math.asin(direction.x)
        cosdec = math.cos(dec) 
        if cosdec > 1e-05:
          ra = math.asin(clamp1(direction.z / cosdec))
          ra2 = math.acos(clamp1(direction.y / cosdec))
        else: ra = ra2 = math.pi/2
        #print(cosdec, direction)
        #print 'arm ' + arm.get_name() + ' ' + str((dec, ra, ra2, cosdec))

        if direction.z > 0: 
          if ra2 < math.pi/2: ra2 = 0
          else: ra2 = math.pi

        arm.jointForearm.setH(-dec * 180/math.pi)
        arm.jointBase.setP(-ra2 * 180/math.pi)

        dec = arm.jointForearm.getH() / 90.0 * 300 + 512
        ra = arm.jointBase.getP()    / 90.0 * 300 + 212
        baseID = arm.baseID
        servos.setAngle({baseID:int(round(ra)), (baseID+1):int(round(dec))})
      return task.again

    def setForearm(self, inc):
        #self.jointForearm.setH(random.random()*180-90)
        self.jointForearm.setH(self.jointForearm.getH() + inc)
    def setBase(self, inc):
        #self.jointBase.setP(random.random()*180)
        self.jointBase.setP(self.jointBase.getP() + inc)

    def push_key(self, key, value):
        """Stores a value associated with a key."""
        self.keys[key] = value

    def update(self, task):
        dt = delta = globalClock.getDt()
        inc = 10
        move_x = delta * inc * -self.keys['a'] + delta * inc * self.keys['d']
        move_z = delta * inc * self.keys['s'] + delta * inc * -self.keys['w']
        move_y = delta * inc * self.keys['q'] + delta * inc * -self.keys['e']
        self.camera.setPos(self.camera, move_x, -move_z, move_y)
        self.heading += (delta * 90 * self.keys['arrow_left'] +
                         delta * 90 * -self.keys['arrow_right'])
        self.pitch += (delta * 90 * self.keys['arrow_up'] +
                       delta * 90 * -self.keys['arrow_down'])
        self.camera.setHpr(self.heading, self.pitch, 0)

        # save ralph's initial position so that we can restore it,
        # in case he falls off the map or runs into something.

        startpos = self.ralph.getPos()

        # If a move-key is pressed, move ralph in the specified direction.

        if self.keys["Rleft"]:
            self.ralph.setH(self.ralph.getH() + 300 * dt)
        if self.keys["Rright"]:
            self.ralph.setH(self.ralph.getH() - 300 * dt)
        if self.keys["Rforward"]:
            self.ralph.setY(self.ralph, -25 * dt)

        # If ralph is moving, loop the run animation.
        # If he is standing still, stop the animation.

        if self.keys["Rforward"] or self.keys["Rleft"] or self.keys["Rright"]:
            if self.isMoving is False:
                self.ralph.loop("run")
                self.isMoving = True
        else:
            if self.isMoving:
                self.ralph.stop()
                self.ralph.pose("walk", 5)
                self.isMoving = False

        return task.cont

game = Game()
game.run()
