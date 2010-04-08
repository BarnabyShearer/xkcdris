#! /usr/bin/env python

"""
Game inspired by http://xkcd.com/724/

@author: bware@iware.co.uk
@licence: http://www.opensource.org/licenses/mit-license.php
"""

import sys
import math
import itertools
import random

import pygame
import pygame.gfxdraw
from pygame import locals as events
from pygame.color import THECOLORS

import pymunk
from pymunk import Vec2d
import pymunk.util

def to_pygame(point):
	"""Small hack to convert pymunk to pygame coordinates"""
	return int(point.x), int(-point.y+400)

def square(point, scale = 20):
	"""Convert unit square at given offest to coordinates"""
	return (
			(point[0]*scale, point[1]*scale),
			(point[0]*scale+scale, point[1]*scale),
			(point[0]*scale+scale, point[1]*scale+scale),
			(point[0]*scale, point[1]*scale+scale),
	)

TETROMINOES = [
	{
		'color': THECOLORS["maroon"],
		'squares': ((-2, 0) , (-1, 0), (0, 0), (1, 0)),
	},
	{
		'color': THECOLORS["darkgray"],
		'squares': ((-2, 0), (-1, 0), (0, 0), (0, -1)),
	},
	{
		'color': THECOLORS["magenta"],
		'squares': ((-2, 0), (-1, 0), (0, 0), (-2, -1)),
	},
	{
		'color': THECOLORS["darkblue"],
		'squares': ((-1, 0), (0, 0), (-1, -1), (0, -1)),
	},
	{
		'color': THECOLORS["green"],
		'squares': ((-2, -1), (-1, 0), (-1, -1), (0, 0)),
	},
	{
		'color': THECOLORS["brown"],
		'squares': ((-2, 0), (-1, 0), (0, 0), (-1, -1)),
	},
	{
		'color': THECOLORS["cyan"],
		'squares': ((-2, 0), (-1, 0), (-1, -1), (0, -1)),
	},
]
class Actor(pymunk.Body):
	""" Rigit-body phsics object that can draw itself via PyGame. """

	def __init__(self, space, pos, shapes, color = THECOLORS["gray"], mass = 1):
		self.color = color
		moment = pymunk.moment_for_poly(
			mass,
			map(
				Vec2d,
				itertools.chain(
					*shapes
				)
			),
			Vec2d(0, 0)
		)
		super(Actor, self).__init__(mass, moment)
		self.position = Vec2d(pos)
		if mass != pymunk.inf:
			space.add(self)

		self.shapes = [
                        pymunk.Poly(self, map(Vec2d, x), Vec2d(0, 0))
		for
			x
		in
			shapes
                ]
		space.add(self.shapes)

	def draw(self, screen):
		""" Draw self on PyGame screen """
		[
			pygame.draw.polygon(
				screen,
				self.color,
				map(
					to_pygame,
					x.get_points()
				)
			)
		for
			x
		in
			self.shapes
		]
		if self.color!=THECOLORS["gray"]:
			for shape in self.shapes:
				points = map (
					to_pygame,
					shape.get_points()
				)
				points.append(points[0]) # close
				a,b = itertools.tee( points )
				next(b, None)
				[
					pygame.draw.aalines(
						screen,
						THECOLORS["black"],
						False,
						(
							x[0],
							(
								x[0][0]+random.uniform(-1,1), 
								x[0][1]+random.uniform(-1,1)
							),
							(
								x[1][0]+random.uniform(-1,1), 
								x[1][1]+random.uniform(-1,1)
							),
							x[1]
						),
						True
					)	
				for
					x
				in
					itertools.izip(a,b)
				]
		
#		if self.color!=THECOLORS["gray"]:
#			[
#				pygame.draw.aalines(
#					screen,
#					THECOLORS["black"],
#					True,
#					map(
#						to_pygame,
#						x.get_points()
#					),
#					True
#				)
#			for
#				x
#			in
#				self.shapes
#			]

class Polyomino(Actor):
	""" Rigid-body physics polyomino. """

	def __init__(self, space, pos, squares, color, mass = 1):
		super(Polyomino, self).__init__(
			space,
			pos,
			map(square, squares),
			color,
			mass,
		)

class Wall(Actor):
	"""
		Rigid-body phisics based on a function.
		Works around the not-concave limit.
	"""

	def __init__(
		self,
		space,
		pos,
		width,
		height,
		color = THECOLORS["gray"],
		mass = 1
	):

		self.width = width
		self.height = height

		super(Wall, self).__init__(
			space,
			pos,
			[x for x in map(self.build, xrange(width)) if x!=None],
			color,
			mass,
		)
	def build(self, pos_x):
		""" Split into shapes """
		if pos_x > 0 and self.height(pos_x-1) == self.height(pos_x):
			#Optimize same-height shapes
			return None
		width = 1
		while (
			pos_x+width <= self.width
		) and (
			self.height(pos_x) == self.height(pos_x+width)
		):
			width = width+1
		return (
				(pos_x, 0),
				(pos_x, self.height(pos_x)),
				(pos_x+width, self.height(pos_x)),
				(pos_x+width, 0)
		)

class Xkcd(object):
	""" Game engine """

	def __init__(self):

		self.actor = None
		self.actors = []

		# Setup PyGame
		pygame.init()
		self.screen = pygame.display.set_mode((300, 400))
		self.clock = pygame.time.Clock()

		# Setup PyMunk
		pymunk.init_pymunk()
		self.space = pymunk.Space(50, 50)
		self.space.gravity = (0.0, -900.0)

		self.space.resize_static_hash()
		self.space.resize_active_hash()

		# Set the stage
		def wall_height(pos_x):
			""" Function to define our wall """
			if pos_x <= 10:
				return 400
			elif pos_x >= 210:
				return 400
			else:
				pos_x = pos_x -110
				return 110 - math.cos(math.asin(pos_x/100.0))*100.0

		self.actors.append(
			Wall(
				self.space,
				(0.0, 0.0),
				300,
				wall_height,
				mass = pymunk.inf
			)
		)

		self.spawn()
		self.space.set_default_collision_handler(self.collision, None, None, None)

	def spawn(self):
		""" Add a new actor """
		self.actor = Polyomino(
			self.space,
			(110, 400),
			**TETROMINOES[random.randint(0, len(TETROMINOES)-1)]
		)
		self.actors.append(self.actor)
		

	def collision(self, space, arbiter):
		""" Handle the first collision of the current actor """
		if self.actor in [x.body for x in arbiter.shapes]:
			if self.actor.position.y >= 390:
				print """Well done. You scored %d.""" % len(self.actors)
				sys.exit()
			self.spawn()
		return True

	def run(self):
		""" Main game loop """
		running = True
		paused = False
		while running:
			for event in pygame.event.get():
				if event.type == events.QUIT:
					running = False
				elif event.type == events.KEYDOWN:
					if event.key == events.K_ESCAPE:
						running = False
					elif event.key == events.K_SPACE:
						paused = not(paused)
					elif self.actor:
						if event.key == events.K_a:
							self.actor.apply_impulse((-100.0, 0.0))
						elif event.key == events.K_d:
							self.actor.apply_impulse((100.0, 0.0))
						elif event.key == events.K_w:
							self.actor.apply_impulse((1.0, 0.0), (0.0, 1000.0))
						elif event.key == events.K_s:
							self.actor.apply_impulse((-1.0, 0.0), (0.0, 1000.0))

			#Draw
			self.screen.lock()

			self.screen.fill(THECOLORS["white"])
    
			for actor in self.actors:
				actor.draw(self.screen)
   
			self.screen.unlock()

			# Update physics
			if not(paused):
				[self.space.step(1.0/60.0/5.) for x in range(5)]
    
			# Flip screen
			pygame.display.flip()
			self.clock.tick(50)
			pygame.display.set_caption("fps: " + str(self.clock.get_fps()))


if __name__ == "__main__":
	Xkcd().run()
