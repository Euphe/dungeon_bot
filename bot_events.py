import persistence
import logging
import items
import util
persistence_controller = persistence.PersistenceController.get_instance()


class BotEvent(object):
	def __init__(self, finished_callback, uid, users):
		self.finished_callback = finished_callback
		self.uid = uid
		self.users = users

		for user in users:
			player = persistence_controller.get_ply(user)
			player.event = uid

	def handle_command(self, user, command, *args):
		print("Base bot event shouldnt handle any messages!")

	def add_user(self, user):
		self.users.append(user)
		player = persistence_controller.get_ply(user)
		player.event = self.uid

	def remove_user(self, user):
		for u in self.users:
			if u.username == user.username and u.id == user.id:
				self.users.remove(u)

		player = persistence_controller.get_ply(user)
		player.event = None

	def free_users(self):
		for user in self.users:
			if persistence_controller.is_registered(user):
				player = persistence_controller.get_ply(user)
				player.event = None # Free all players from event

	def finish(self):
		self.free_users()
		self.finished_callback(self.uid)

class RegistrationEvent(BotEvent):

	steps = [
		"name",
		"race", 
		"combat_class"
	]

	def __init__(self, finished_callback, uid, user):
		BotEvent.__init__(self, finished_callback, uid, [user])
		self.user = user
		self.current_step = 0
		self.new_player = persistence_controller.get_ply(user)
		self.greeting_message = 'You can restart the registration at any time by sending "restart".\nLet\'s begin.\nWhat is your name?'
		

	def handle_command(self, user, command, *args):
		if command == "restart":
			self.current_step = 0
			return("Let's begin. What is your name?")

		if self.current_step == 0:
			self.new_player.name = (command + " " + " ".join([str(arg) for arg in args])).strip().title()
			self.current_step+=1
			return("What is your race?")

		elif self.current_step == 1:
			self.new_player.race = command
			self.current_step+=1
			return("What is your class?")

		elif self.current_step == 2:
			self.new_player.combat_class = command
			club = items.PrimaryWeapon("club", "A rough wooden club, good enough to break a skull!", "blunt", {"damage" : "1d3", "accuracy" : "3d6"}, ["swing"])
			self.new_player.inventory = [club]
			self.finish()
			return('Registration complete! Try "examine" to see your stats, "inventory" to see your items.')
			
			

class InventoryEvent(BotEvent):

	allowed_commands = {
		"examine": "shows your stats and inventory","ex": "shows your stats and inventory","stats": "shows your stats and inventory",
		"examine [item]": "shows an item's stats", "ex [item]": "shows an item's stats", 
		"equip [item]": "equips an item","eq [item]": "equips an item",
		"unequip [item]": "equips an item","uneq [item]": "unequips an item",
		"use [item]": "uses an item (such as a potion)", "u [item]": "uses an item (such as a potion)",
		"destroy [item]": "destroys an item","drop [item]": "destroys an item",
		"give [item] [username/playername]": "gives an item to another player",

		"info": "shows help","help": "shows help","h": "shows help",
		"back": "closes inventory","abort": "closes inventory","ab": "closes inventory","b": "closes inventory",
	}

	def __init__(self, finished_callback, uid, user):
		BotEvent.__init__(self, finished_callback, uid, [user])
		self.user = user
		self.player = persistence_controller.get_ply(user)
		self.greeting_message = 'You can close inventory at any time by sending "back" or "abort".'

	def find_item(self, itemname, player, inventory_only = False):
		all_items = self.player.inventory.copy()
		if not inventory_only:
			all_items += list(player.equipment.values())

		for item in all_items:
			if item and item.name == itemname:
				return True, item

		error_text = "No such item in your inventory"
		if not inventory_only:
			error_text += "or equipment."
		else:
			error_text += "."
		return False, error_text


	def handle_command(self, user, command, *args):
		

		if (command in ["help","info","h"]):
			return(util.print_available_commands(self.allowed_commands))

		elif (command in ["examine","ex","stats","st"]):
			if len(args) == 0:
				desc = (persistence_controller.get_ply(self.user)).examine_self()
				desc += "\n"+self.player.examine_equipment()
				desc += self.player.examine_inventory()
				return desc
			elif len(args) > 0:
				found, item = self.find_item(" ".join(args), self.player)
				if found:
					msg = item.examine_self()
					return(msg)
				else:
					return item

		elif (command in ["equip", "eq"]):
			if len(args) == 0:
				return("Specify an item to equip.")
			elif len(args) > 0:
				found, item = self.find_item(" ".join(args), self.player, True)
				if found:
					msg = item.equip(self.player)
					return(msg)
				else:
					return item

		elif (command in ["unequip", "uneq"]):
			if len(args) == 0:
				return("Specify an item to unequip.")
			elif len(args) > 0:
				found, item = self.find_item(" ".join(args), self.player)
				if found:
					msg = item.unequip(self.player)
					return(msg)
				else:
					return item

		elif (command in["use", "u"]):
			if len(args) == 0:
				return("Specify an item to use.")
			elif len(args) > 0:
				found, item = self.find_item(" ".join(args), self.player)
				if found:
					msg = item.use(self.player)
					return(msg)
				else:
					return item

		elif (command in ['destroy', 'drop']):
			if len(args) == 0:
				return("Specify an item to destroy.")
			elif len(args) > 0:
				found, item = self.find_item(" ".join(args), self.player)
				if found:
					msg = item.destroy(self.player)
					return(msg)
				else:
					return item

		elif (command == "give"):
			return "WIP FEATURE"

		elif (command in ["back", "abort", "ab", "b"]):
			self.finish()
			return "Closed inventory"

		return 'Unknown command, try "help"'

class DungeonLobbyEvent(BotEvent):
	allowed_commands = {
		"start": "starts the dungeon crawl", "st": "starts the dungeon crawl",
		"info": "shows help","help": "shows help","h": "shows help",
		"back": "leaves lobby","abort": "leaves lobby","ab": "leaves lobby","b": "leaves lobby", "leave": "leaves lobby"
	}

	def __init__(self, finished_callback, uid, total_users):
		BotEvent.__init__(self, finished_callback, uid, [])
		self.greeting_message = 'A dungeon crawl will start once there are enough players (%d). Use "abort" to leave, "start" to begin.'%(total_users)
		self.total_users = total_users

	def handle_command(self, user, command, *args):
		if (command in ["help","info","h"]):
			return(util.print_available_commands(self.allowed_commands))
		if (command in ["back","abort","b", "leave", "ab"]):
			return(self.remove_user(user))
		if (command in ["start"]):
			return(self.start_crawl())
		return 'Unknown command, try "help"'

	def is_enough_players(self):
		if len(self.users) < self.total_users:
			return False	
		return True

	def add_user(self, user):
		super(DungeonLobbyEvent, self).add_user(user)
		broadcast = []
		msg = "User %s joined the lobby"%(user.username)

		msg_enough = 'The lobby has enough players to start, use "start" command to proceed'
		msg_not_enough = 'The lobby needs %d more players to start'%( self.total_users - len(self.users) )

		broadcast.append([user, "You were added to lobby %s"%(self.uid)])
		broadcast.append([user, self.greeting_message])
		for u in self.users:
			if u != user:
				broadcast.append([u, msg])
			if self.is_enough_players():
				broadcast.append([u, msg_enough])
			else:
				broadcast.append([u, msg_not_enough])

		return broadcast

	def remove_user(self, user):
		super(DungeonLobbyEvent, self).remove_user(user)
		broadcast = []
		msg_enough = 'The lobby has enough players to start, use "start" command to proceed'
		msg_not_enough = 'The lobby needs %d more players to start'%( self.total_users - len(self.users) )
		msg = "User %s left the lobby"%(user.username)

		broadcast.append([user, "You were removed from lobby %s"%(self.uid)])
		for u in self.users:
			if u != user:
				broadcast.append([u, msg])
				if self.is_enough_players():
					broadcast.append([u, msg_enough])
				else:
					broadcast.append([u, msg_not_enough])

		if len(self.users) == 0:
			self.finish()

		return broadcast

	def move_players_to_dungeon(self, uid):
		for user in self.users:
			ply = persistence_controller.get_ply(user)
			ply.event = uid

	def start_crawl(self):
		return self.finished_callback(self.uid)

class DungeonCrawlEvent(BotEvent):
	def __init__(self, finished_callback, uid, users, dungeon):
		BotEvent.__init__(self, finished_callback, uid, users)
		self.greeting_message = 'You are entering %s.%s\n'%(dungeon.name, dungeon.description)
		self.dungeon = dungeon
		self.can_advance = False
		self.non_combat_events = {}

	allowed_commands = {
		"advance": "move to next room", "adv": "move to next room",
		"inventory": "shows your inventory", "inv": "shows your inventory",
		"examine": "shows your stats", "ex": "shows your stats", "stats": "shows your stats","st": "shows your stats",
		"examine [character]": "shows a chracter's stats", "ex [character]": "shows a chracter's stats", "stats [character]": "shows a chracter's stats","st [character]": "shows a chracter's stats",
		"info": "shows help","help": "shows help","h": "shows help",
		"back": "leaves dungeon crawl","abort": "leaves dungeon crawl","ab": "leaves dungeon crawl","b": "leaves dungeon crawl", "leave": "leaves dungeon crawl",
		"say [message]": "sends a message to your fellow dungeon crawlers", "s [message]": "sends a message to your fellow dungeon crawlers", 
		"levelup": "opens the level up dialogue", "lvl": "opens the level up dialogue", 
	}

	def check_if_can_advance(self):
		if len(list(self.non_combat_events.keys())) > 0:
			return False
		return True

	def remove_user(self, user):
		super(BotEvent, self).remove_user(user)
		broadcast = []
		msg = 'Pathetic looser %s ran away from the dungeon like a pussy he is'%(persistence_controller.get_ply(user))

		broadcast.append([user, "You were removed from lobby %s"%(self.uid)])
		for u in self.users:
			if u != user:
				broadcast.append([u, msg])

		if len(self.users) == 0:
			self.finish()

		return broadcast

	def advance_room(self):
		if not self.can_advance:
			msg = "Can't advance, someone is inventory or leveling up"
			broadcast = [(u, msg) for u in self.users]
			return broadcast

	def open_levelup(self, user):
		pass

	def open_inventory(self, user):
		uid = util.get_uid()

		def inv_over_callback(uid):
			for event in list(self.non_combat_events.keys()):
				if self.non_combat_events[event] == uid:
					del self.non_combat_events[event]
					break

		inv = InventoryEvent(inv_over_callback, uid, user) #Create an inventory event
		self.non_combat_events[user.username] = inv
		logging.debug("Inventory event  %s created within dungeon %s."%(uid, self.uid))

		broadcast = []
		msg = ' %s is rummaging in his inventory.'%(persistence_controller.get_ply(user))

		broadcast.append([user, inv.greeting_message])
		for u in self.users:
			if u != user:
				broadcast.append([u, msg])
		return(broadcast)

	def handle_command(self, user, command, *args):

		if user.username in list(self.non_combat_events.keys()):
			return self.non_combat_events[user.username].handle_command(user, command, *args)
		if (command in ["help","info","h"]):
			return(util.print_available_commands(self.allowed_commands))
		if (command in ["back","abort","b", "leave", "ab"]):
			return(self.remove_user(user))
		if (command in ["advance","adv"]):
			return(self.advance_room())
		if (command in ["inventory","inv"]):
			return(self.open_inventory(user))
		if (command in ["levelup","lvl"]):
			return(self.open_levelup(user))
		if (command in ["examine", "stats", "ex", "st"]):
			if len(args) > 0:
				argument = " ".join(args)
				if argument=="self" or argument == user.username or argument == persistence_controller.get_ply(user).name:
					return (persistence_controller.get_ply(user).examine_self())
				else:
					target_user = None
					for u in self.users:
						target_ply = persistence_controller.get_ply(u)
						if u.username == argument or persistence_controller.get_ply(u).name == argument:
							target_user = u
							break
					if target_user:
						return (target_ply.examine_self())
					else:
						return "No such player or user in that dungeon"
		return 'Unknown command, try "help"'