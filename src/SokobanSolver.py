import subprocess
from lib.theoryWriter import TheoryWriter
import lib.text2dimacs 

class SokobanSolver(object):

	MINISAT_PATH = 'lib/minisat/win/minisat.exe'
	CNF_FILE = 'cnf.txt'
	DIMACS_FILE = 'dimacs.txt'
	DIMACS_VARS_FILE = 'variables.txt'
	MINISAT_OUT_FILE = 'out.txt'

	def __init__(self, map_name):
		self.map_data = {}
		self.load_map(map_name)
		self.coords = self.generate_coords()

	def solve(self):
		ok = False
		iteration = 1
		sol=[]
		while not ok:
			print('ITERATION:', iteration)
			theory = TheoryWriter(self.CNF_FILE)
			print('Writing theory ...')
			self.encode(theory, iteration)
			theory.close()
			print('Translating to DIMACS ...')
			lib.text2dimacs.translate(self.CNF_FILE, self.DIMACS_FILE)
			print('Solving ...')
			args = (self.MINISAT_PATH, self.DIMACS_FILE, self.MINISAT_OUT_FILE)
			popen = subprocess.Popen(args, stdout=subprocess.PIPE)
			popen.wait()
			ok,sol=self.spracuj()
			iteration += 1
		print('DONE')
		for x in sol:
			print(x)

	def spracuj(self):
		line=''
		with open(self.MINISAT_OUT_FILE) as f:
			sat=f.readline()
			line=f.readline()
			if sat == 'UNSAT':
				return (False, [])
		line=line.strip().split()
		variables={}
		var=0
		res=[]
		with open(self.DIMACS_VARS_FILE) as f:
			for l in f:
				if var==0:
					var=int(l)
				else:
					variables[var]=l.strip()
					var=0
		for l in line:
			x=int(l)
			if x>0:
				pred=variables.get(x,'null')
				res.append(pred)
		return (True, res)

	def encode(self, theory, iteration):
		self.encodeInitState(theory)
		self.encodeGoal(theory, iteration)
		theory.writeComment('RULES')
		for step in range(1, iteration + 1):
			theory.writeComment(
			    'Na jednom policku moze byt bud hrac alebo nic alebo nejaky z boxov')

			# for XY in self.coords:
			#     if XY not in self.map_data['walls']:
			#         theory.writeLiteral(self.player(XY, step))
			# theory.finishClause()

			# for box_id in range(len(self.map_data['boxes'])):
			#     for XY in self.coords:
			#         if XY not in self.map_data['walls']:
			#             theory.writeLiteral(self.at(box_id+1, XY, step))
			# theory.finishClause()

			theory.writeComment(
			    'empty(XY, state) or player(XY, state) or at(box_id, XY, state)')
			for XY in self.coords:
				if XY not in self.map_data['walls']:
					clause = [self.empty(XY, step), self.player(XY, step)]
					for box_id in range(len(self.map_data['boxes'])):
							clause.append(self.at(box_id+1, XY, step))
					theory.writeClause(clause)
				else:
					theory.writeClause([self.neg(self.empty(XY, step))])

			self.encode_player_pos(theory, step)
			self.encode_box_pos(theory, step)
			self.encode_position_exclusivity(theory, step)
			self.encode_actions(theory, step)

	def encode_box_pos(self, theory, step):
		theory.writeComment(
		    'Ak je box na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
		for box_id in range(len(self.map_data['boxes'])):
			for c1 in range(len(self.coords)):
				for c2 in range(c1+1, len(self.coords)):
					if self.coords[c1] not in self.map_data['walls'] and self.coords[c2] not in self.map_data['walls']:
						theory.writeClause([
							self.neg(self.at(box_id+1, self.coords[c1], step)),
							self.neg(self.at(box_id+1, self.coords[c2], step))
						])

	def encode_player_pos(self, theory, step):
		theory.writeComment(
		    'Ak je hrac na nejakej pozicii, nemoze byt zaroven na druhej pozicii')
		for c1 in range(len(self.coords)):
			for c2 in range(c1 + 1, len(self.coords)):
				if self.coords[c1] not in self.map_data['walls'] and self.coords[c2] not in self.map_data['walls']:
					theory.writeClause([
						self.neg(self.player(self.coords[c1], step)),
						self.neg(self.player(self.coords[c2], step))
					])

	def encode_position_exclusivity(self, theory, step):
		theory.writeComment('Na jednom policku moze byt maximalne bud hrac, nic, box')
		for XY in self.coords:
			if XY not in self.map_data['walls']:
				theory.writeClause([self.neg(self.player(XY, step)), self.neg(self.empty(XY, step))])
				for box_id in range(len(self.map_data['boxes'])):
					theory.writeClause([self.neg(self.player(XY, step)), self.neg(self.at(box_id+1, XY, step))])
					theory.writeClause([self.neg(self.empty(XY, step)),
																self.neg(self.at(box_id+1, XY, step))])

	def encode_action_move(self, theory, step):
		theory.writeComment('Action move(fromXY, toXY, step)')
		for fromXY in self.coords:
			for toXY in self.coords:
				if self.is_adjacent(fromXY, toXY):
					if fromXY not in self.map_data['walls'] and toXY not in self.map_data['walls']:
						# P+
						theory.writeClause([
							self.neg(self.move(fromXY, toXY, step)), 
							self.player(fromXY, step-1)
						])
						theory.writeClause([
							self.neg(self.move(fromXY, toXY, step)), 
							self.empty(toXY, step-1)
						])
						# P-
						# for box_id in range(len(self.map_data['boxes'])):
						#     theory.writeClause([
						#         self.neg(self.move(fromXY, toXY, step)), 
						#         self.neg(self.at(box_id+1, toXY, step-1))
						#     ])
						# theory.writeClause([
						#     self.neg(self.move(fromXY, toXY, step)), 
						#     self.neg(self.player(toXY, step-1))
						# ])
						# E+
						theory.writeClause([
								self.neg(self.move(fromXY, toXY, step)), 
								self.player(toXY, step)
						])
						theory.writeClause([
								self.neg(self.move(fromXY, toXY, step)), 
								self.empty(fromXY, step)
						])
						# E-
						theory.writeClause([
								self.neg(self.move(fromXY, toXY, step)), 
								self.neg(self.empty(toXY, step))
						])
						# theory.writeClause([
						#     self.neg(self.move(fromXY, toXY, step)), 
						#     self.neg(self.player(fromXY, step))
						# ])
						# theory.writeClause([
						#     self.neg(self.move(fromXY, toXY, step)), 
						#     self.at(1, (1,2), step)
						# ])
						for box_id in range(len(self.map_data['boxes'])):
								theory.writeClause([
										self.neg(self.move(fromXY, toXY, step)), 
										self.neg(self.in_target(box_id+1, step))
								])
						# for box_id in range(len(self.map_data['boxes'])):
						#     theory.writeClause([
						#         self.neg(self.move(fromXY, toXY, step)), 
						#         self.neg(self.at(box_id+1, fromXY, step))
						#     ])

	def encode_action_push(self, theory, step):
		theory.writeComment('Action push(box, playerXY, fromXY, toXY, step)')
		for box_id in range(len(self.map_data['boxes'])):
				for playerXY in self.coords:
						for fromXY in self.coords:
								for toXY in self.coords:
										if (self.is_inline(playerXY, fromXY, toXY) and
												playerXY not in self.map_data['walls'] and
												fromXY not in self.map_data['walls'] and
												toXY not in self.map_data['walls']):
                            # P+
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(toXY, step-1)
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(playerXY, step-1)
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, fromXY, step-1)
                            ])
                            # P-
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.target(toXY))
                            ])
                            # E+
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(fromXY, step)
													])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, toXY, step)
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(playerXY, step)
                            ])
                            # E-
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.empty(toXY, step))
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.player(playerXY, step))
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.at(box_id+1, fromXY, step))
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step))
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step-1))
                            ])

	def encode_action_push_t(self, theory, step):
		theory.writeComment('Action push_t(box, playerXY, fromXY, toXY, step)')
		for box_id in range(len(self.map_data['boxes'])):
				for playerXY in self.coords:
						for fromXY in self.coords:
								for toXY in self.coords:
										if (self.is_inline(playerXY, fromXY, toXY) and
												playerXY not in self.map_data['walls'] and
												fromXY not in self.map_data['walls'] and
												toXY not in self.map_data['walls']):
                            # P+
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(toXY, step-1)
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(playerXY, step-1)
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, fromXY, step-1)
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.target(toXY)
                            ])
													theory.writeClause([
                                self.neg(self.push(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.in_target(box_id+1, step-1))
                            ])
                            # E+
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.player(fromXY, step)
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.at(box_id+1, toXY, step)
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.empty(playerXY, step)
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.in_target(box_id+1, step)
                            ])
                            # E-
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.empty(toXY, step))
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.player(playerXY, step))
                            ])
													theory.writeClause([
                                self.neg(self.push_t(box_id+1, playerXY, fromXY, toXY, step)),
                                self.neg(self.at(box_id+1, fromXY, step))
                            ])

	def encode_actions(self, theory, step):
		self.encode_action_move(theory, step)
		self.encode_action_push(theory, step)
		self.encode_action_push_t(theory, step)
		actions = []
		for fromXY in self.coords:
				for toXY in self.coords:
						if (self.is_adjacent(fromXY, toXY) and
								fromXY not in self.map_data['walls'] and
								toXY not in self.map_data['walls']):
								actions.append(self.move(fromXY, toXY, step))
		for box_id in range(len(self.map_data['boxes'])):
				for playerXY in self.coords:
						for fromXY in self.coords:
								for toXY in self.coords:
										if (self.is_inline(playerXY, fromXY, toXY) and
												playerXY not in self.map_data['walls'] and
												fromXY not in self.map_data['walls'] and
												toXY not in self.map_data['walls']):
												actions.append(self.push(box_id+1, playerXY, fromXY, toXY, step))
												actions.append(self.push_t(box_id+1, playerXY, fromXY, toXY, step))
		theory.writeComment('At least one action happens')
		theory.writeClause(actions)
		theory.writeComment('Action exclusivity')
		for action1 in range(len(actions)):
				for action2 in range(action1+1, len(actions)):
						if action1 != action2:
								theory.writeClause([self.neg(actions[action1]), self.neg(actions[action2])])
        
	def encodeGoal(self, w, N):
		w.writeComment('Goal')
		# w.writeClause([self.player((1,3), N)])
		for box_id in range(len(self.map_data['boxes'])):
			w.writeLiteral(self.in_target(box_id+1, N))
			w.finishClause()
    
	def encodeInitState(self, theory):
		theory.writeComment('Initial state loaded from the map')
		theory.writeComment('Targets on the map (fact)')
		for XY in self.coords:
				if XY in self.map_data['targets']:
						theory.writeLiteral(self.target(XY))
				else:
						theory.writeLiteral(self.neg(self.target(XY)))
				theory.finishClause()
		theory.writeComment('Initial position of the player loaded from the map')
		for XY in self.coords:
				if XY == self.map_data['sokoban']:
						theory.writeLiteral(self.player(XY, 0))
				else:
						theory.writeLiteral(self.neg(self.player(XY, 0)))
				theory.finishClause()
		theory.writeComment('Initial boxes position loaded from the map')
		for XY in self.coords:
				for index,box in enumerate(self.map_data['boxes']):
						if XY == box:
								theory.writeLiteral(self.at(index+1, XY, 0))
						else:
								theory.writeLiteral(self.neg(self.at(index+1, XY, 0)))
						theory.finishClause()
		theory.writeComment('Boxes in the target')
		for index, box in enumerate(self.map_data['boxes']):
				if box in self.map_data['targets']:
						theory.writeLiteral(self.in_target(index+1, 0))
				else:
						theory.writeLiteral(self.neg(self.in_target(index+1, 0)))
				theory.finishClause()
		theory.writeComment('Initial empty squares loaded from the map')
		for XY in self.coords:
				if (XY not in self.map_data['walls'] and 
						XY not in self.map_data['boxes'] and 
						XY != self.map_data['sokoban']):
						theory.writeLiteral(self.empty(XY, 0))
				else:
						theory.writeLiteral(self.neg(self.empty(XY, 0)))
				theory.finishClause()
    
	def push(self, box_id, playerXY, fromXY, toXY, step):
		return ('push(box{},{}_{},{}_{},{}_{},{})'
                        .format(box_id, playerXY[0], playerXY[1], fromXY[0], fromXY[1], toXY[0], toXY[1], step))

	def push_t(self, box_id, playerXY, fromXY, toXY, step):
		return ('push_t(box{},{}_{},{}_{},{}_{},{})'
                        .format(box_id, playerXY[0], playerXY[1], fromXY[0], fromXY[1], toXY[0], toXY[1], step))

	def move(self, fromXY, toXY, step):
		return 'move({}_{},{}_{},{})'.format(fromXY[0], fromXY[1], toXY[0], toXY[1], step)

	def empty(self, XY, step):
		return 'empty({}_{},{})'.format(XY[0], XY[1], step)

	def player(self, XY, step):
		return 'player({}_{},{})'.format(XY[0], XY[1], step)

	def at(self, box_id, XY, step):
		return 'at(box{},{}_{},{})'.format(box_id, XY[0], XY[1], step)

	def target(self, XY):
			return 'target({}_{})'.format(XY[0], XY[1])

	def in_target(self, box_id, step):
		return 'in_target(box{},{})'.format(box_id, step)

	def wall(self, XY):
		return 'wall({}_{})'.format(XY[0], XY[1])

	def neg(self, predicate):
		return '-' + predicate

	def load_map(self, file_name):
		self.map_data = {
				'map_size': (),
				'walls': [],
				'sokoban': (),
				'boxes': [],
				'targets': []
		}
		with open(file_name) as f:
				l = 0
				for line in f:
						ch = 0
						for char in line:
								if char == '#':
										self.map_data['walls'].append((l,ch))
								elif char == 'S':
										self.map_data['sokoban'] = (l,ch)
								elif char == 'X':
										self.map_data['sokoban'] = (l,ch)
										self.map_data['targets'].append((l,ch))
								elif char == 'B':
										self.map_data['boxes'].append((l,ch))
								elif char == 'T':
										self.map_data['targets'].append((l,ch))
								ch += 1 
						l += 1
				self.map_data['map_size'] = (l,ch)
    
	def generate_coords(self):
		coords = []
		for x in range(self.map_data['map_size'][0]):
				for y in range(self.map_data['map_size'][1]):
						coords.append((x,y))
		return coords

	def is_inline(self, playerXY, fromXY, toXY):
		if not self.is_adjacent(fromXY, toXY) or not self.is_adjacent(playerXY, fromXY) or playerXY == toXY:
				return False
		if fromXY[0] == toXY[0]:
				return fromXY[0] == playerXY[0]
		if fromXY[1] == toXY[1]:
				return fromXY[1] == playerXY[1]
		return False

	def is_adjacent(self, c1, c2):
		if c1 == c2:
				return False
		if c1[0] == c2[0] and c1[1] == c2[1]+1:
				return True
		if c1[0] == c2[0] and c1[1] == c2[1]-1:
				return True
		if c1[1] == c2[1] and c1[0] == c2[0]+1:
				return True
		if c1[1] == c2[1] and c1[0] == c2[0]-1:
				return True
		return False

if __name__ == "__main__":
	ss = SokobanSolver('maps/map3.txt')
	ss.solve()
