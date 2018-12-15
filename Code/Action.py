# Actions
# All permanent changes to game state are reified as actions.

try:
    import GlobalConstants as GC
    import configuration as cf
    import static_random
    import StatusObject, Banner, LevelUp, Weapons
    import Utility, ItemMethods, UnitObject
except ImportError:
    from . import GlobalConstants as GC
    from . import configuration as cf
    from . import static_random
    from . import StatusObject, Banner, LevelUp, Weapons
    from . import Utility, ItemMethods, UnitObject

class Action(object):
    run_on_load = False

    def __init__(self):
        pass

    # When used normally
    def do(self, gameStateObj):
        pass

    # When put in forward motion by the turnwheel
    def execute(self, gameStateObj):
        self.do(gameStateObj)

    # When put in reverse motion by the turnwheel
    def reverse(self, gameStateObj):
        pass

    def update(self, gameStateObj):
        pass

    def serialize(self, gameStateObj):
        ser_dict = {}
        for attr in self.__dict__.items():
            # print(attr)
            name, value = attr
            if isinstance(value, UnitObject.UnitObject):
                value = ('Unit', value.id)
            elif isinstance(value, ItemMethods.ItemObject):
                for unit in gameStateObj.allunits:
                    if value in unit.items:
                        value = ('Item', unit.id, unit.items.index(value))
                        break
                else:
                    if value in gameStateObj.convoy:
                        value = ('ConvoyItem', gameStateObj.convoy.index(value))
                    else:
                        value = ('UniqueItem', value.serialize())
            elif isinstance(value, StatusObject.StatusObject):
                for unit in gameStateObj.allunits:
                    if value in unit.status_effects:
                        value = ('Status', unit.id, unit.status_effects.index(value))
                        break
                else:
                    value = ('UniqueStatus', value.serialize())
            elif isinstance(value, Action):  # This only works if two actions never refer to one another
                value = ('Action', value.serialize(gameStateObj))
            else:
                value = ('Generic', value)
            ser_dict[name] = value
        # print(ser_dict)
        return (self.__class__.__name__, ser_dict)

    @classmethod
    def deserialize(cls, ser_dict, gameStateObj):
        self = cls.__new__(cls)
        # print(cls.__name__)
        for name, value in ser_dict.items():
            if value[0] == 'Unit':
                setattr(self, name, gameStateObj.get_unit_from_id(value[1]))
            elif value[0] == 'Item':
                unit = gameStateObj.get_unit_from_id(value[1])
                setattr(self, name, unit.items[value[2]])
            elif value[0] == 'ConvoyItem':
                setattr(self, name, gameStateObj.convoy[value[1]])
            elif value[0] == 'UniqueItem':
                setattr(self, name, ItemMethods.deserialize(value[1]))
            elif value[0] == 'Status':
                unit = gameStateObj.get_unit_from_id(value[1])
                setattr(self, name, unit.status_effects[value[2]])
            elif value[0] == 'UniqueStatus':
                setattr(self, name, StatusObject.deserialize(value[1]))
            elif value[0] == 'Action':
                setattr(self, name, Action.deserialize(value[1][1], gameStateObj))
            else:
                setattr(self, name, value[1])
        return self

class Move(Action):
    """
    A basic, user-directed move
    """
    def __init__(self, unit, new_pos, path=None):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

        self.prev_movement_left = self.unit.movement_left
        self.new_movement_left = None

        self.path = path
        self.hasMoved = self.unit.hasMoved

    def do(self, gameStateObj):
        gameStateObj.moving_units.add(self.unit)
        self.unit.lock_active()
        self.unit.sprite.change_state('moving', gameStateObj)
        # Remove tile statuses
        self.unit.leave(gameStateObj)
        if self.path is None:
            self.unit.path = gameStateObj.cursor.movePath
        else:
            self.unit.path = self.path
        self.unit.play_movement_sound(gameStateObj)

    def execute(self, gameStateObj):
        self.unit.leave(gameStateObj)
        if self.new_movement_left is not None:
            self.unit.movement_left = self.new_movement_left
        self.unit.hasMoved = True
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.new_movement_left = self.unit.movement_left
        self.unit.movement_left = self.prev_movement_left
        self.unit.hasMoved = self.hasMoved
        self.unit.position = self.old_pos
        self.unit.path = []
        self.unit.arrive(gameStateObj)

# Just another name for move
class CantoMove(Move):
    pass

class Teleport(Action):
    """
    A script directed move, no animation
    """
    def __init__(self, unit, new_pos):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

    def do(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.old_pos
        self.unit.arrive(gameStateObj)

class Warp(Action):
    def __init__(self, unit, new_pos):
        self.unit = unit
        self.old_pos = self.unit.position
        self.new_pos = new_pos

    def do(self, gameStateObj):
        self.unit.sprite.set_transition('warp_move')
        self.unit.sprite.set_next_position(self.new_pos)
        gameStateObj.map.initiate_warp_flowers(self.unit.position)

    def execute(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.new_pos
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.position = self.old_pos
        self.unit.arrive(gameStateObj)

class FadeMove(Warp):
    def do(self, gameStateObj):
        self.unit.sprite.set_transition('fade_move')
        self.unit.sprite.set_next_position(self.new_pos)

class ArriveOnMap(Action):
    def __init__(self, unit, pos):
        self.unit = unit
        self.pos = pos

    def do(self, gameStateObj):
        self.unit.position = self.pos
        self.unit.place_on_map(gameStateObj)
        self.unit.arrive(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.remove_from_map(gameStateObj)
        self.unit.position = None

class WarpIn(ArriveOnMap):
    def do(self, gameStateObj):
        self.unit.position = self.pos
        self.unit.sprite.set_transition('warp_in')
        gameStateObj.map.initiate_warp_flowers(self.pos)
        self.unit.place_on_map(gameStateObj)
        self.unit.arrive(gameStateObj)

class FadeIn(ArriveOnMap):
    def do(self, gameStateObj):
        self.unit.position = self.pos
        if gameStateObj.map.on_border(self.pos) and gameStateObj.map.tiles[self.pos].name not in ('Stairs', 'Fort'):
            self.unit.sprite.spriteOffset = [num*GC.TILEWIDTH for num in gameStateObj.map.which_border(self.pos)]
            self.unit.sprite.set_transition('fake_in')
        else:
            self.unit.sprite.set_transition('fade_in')
        self.unit.place_on_map(gameStateObj)
        self.unit.arrive(gameStateObj)

class LeaveMap(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_pos = self.unit.position

    def do(self, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.remove_from_map(gameStateObj)
        self.unit.position = None

    def reverse(self, gameStateObj):
        self.unit.position = self.old_pos
        self.unit.place_on_map(gameStateObj)
        self.unit.arrive(gameStateObj)

class Wait(Action):
    def __init__(self, unit):
        self.unit = unit
        self.hasMoved = unit.hasMoved
        self.hasTraded = unit.hasTraded
        self.hasAttacked = unit.hasAttacked
        self.finished = unit.finished

    def do(self, gameStateObj):
        self.unit.hasMoved = True
        self.unit.hasTraded = True
        self.unit.hasAttacked = True
        self.unit.finished = True
        self.unit.current_move_action = None

    def reverse(self, gameStateObj):
        self.unit.hasMoved = self.hasMoved
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = self.hasAttacked
        self.unit.finished = self.finished
        # print(self.unit.hasMoved, self.unit.hasTraded, self.unit.hasAttacked)

class Reset(Action):
    def __init__(self, unit):
        self.unit = unit
        self.hasMoved = unit.hasMoved
        self.hasTraded = unit.hasTraded
        self.hasAttacked = unit.hasAttacked
        self.finished = unit.finished
        self.hasRunMoveAI = unit.hasRunMoveAI
        self.hasRunAttackAI = unit.hasRunAttackAI
        self.hasRunGeneralAI = unit.hasRunGeneralAI

    def do(self, gameStateObj):
        self.unit.reset()

    def reverse(self, gameStateObj):
        self.unit.hasMoved = self.hasMoved
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = self.hasAttacked
        self.unit.finished = self.finished
        self.unit.hasRunMoveAI = self.hasRunMoveAI
        self.unit.hasRunAttackAI = self.hasRunAttackAI
        self.unit.hasRunGeneralAI = self.hasRunGeneralAI

# === RESCUE ACTIONS ==========================================================
class Rescue(Action):
    def __init__(self, unit, rescuee):
        self.unit = unit
        self.rescuee = rescuee
        self.old_pos = self.rescuee.position

    def do(self, gameStateObj):
        self.unit.TRV = self.rescuee.id
        self.unit.strTRV = self.rescuee.name
        if Utility.calculate_distance(self.unit.position, self.rescuee.position) == 1:
            self.rescuee.sprite.set_transition('rescue')
            self.rescuee.sprite.spriteOffset = [(self.unit.position[0] - self.old_pos[0]), 
                                                (self.unit.position[1] - self.old_pos[1])]
        else:
            self.rescuee.leave(gameStateObj)
            self.rescuee.position = None
        self.unit.hasAttacked = True
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)

    def execute(self, gameStateObj):
        self.unit.TRV = self.rescuee.id
        self.unit.strTRV = self.rescuee.name
        self.rescuee.leave(gameStateObj)
        self.rescuee.position = None
        self.unit.hasAttacked = True
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)

    def reverse(self, gameStateObj):
        self.rescuee.position = self.old_pos
        self.rescuee.arrive(gameStateObj)
        self.unit.hasAttacked = False
        self.unit.unrescue(gameStateObj)

class Drop(Action):
    def __init__(self, unit, droppee, pos):
        self.unit = unit
        self.droppee = droppee
        self.pos = pos
        self.hasTraded = self.unit.hasTraded

    def do(self, gameStateObj):
        self.droppee.position = self.pos
        self.droppee.arrive(gameStateObj)
        self.droppee.wait(gameStateObj, script=False)
        self.droppee.hasAttacked = True
        self.unit.hasTraded = True  # Can no longer do everything
        if Utility.calculate_distance(self.unit.position, self.pos) == 1:
            self.droppee.sprite.set_transition('fake_in')
            self.droppee.sprite.spriteOffset = [(self.unit.position[0] - self.pos[0])*GC.TILEWIDTH,
                                                (self.unit.position[1] - self.pos[1])*GC.TILEHEIGHT]
        self.unit.unrescue(gameStateObj)

    def execute(self, gameStateObj):
        self.droppee.position = self.pos
        self.droppee.arrive(gameStateObj)
        self.droppee.wait(gameStateObj, script=False)
        self.droppee.hasAttacked = True
        self.unit.hasTraded = True  # Can no longer do everything
        self.unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.TRV = self.droppee.id
        self.unit.strTRV = self.droppee.name
        self.unit.hasTraded = self.hasTraded
        self.unit.hasAttacked = False
        self.droppee.position = None
        self.droppee.leave(gameStateObj)
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)

class Give(Action):
    def __init__(self, unit, other_unit):
        self.unit = unit
        self.other_unit = other_unit

    def do(self, gameStateObj):
        self.other_unit.TRV = self.unit.TRV
        self.other_unit.strTRV = self.unit.strTRV
        self.unit.hasAttacked = True
        if 'savior' not in self.other_unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.other_unit, gameStateObj)
        self.unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.unit.TRV = self.other_unit.TRV
        self.unit.strTRV = self.other_unit.strTRV
        self.unit.hasAttacked = False
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)
        self.other_unit.unrescue(gameStateObj)

class Take(Action):
    def __init__(self, unit, other_unit):
        self.unit = unit
        self.other_unit = other_unit
        self.hasTraded = self.unit.hasTraded

    def do(self, gameStateObj):
        self.unit.TRV = self.other_unit.TRV
        self.unit.strTRV = self.other_unit.strTRV
        self.unit.hasTraded = True
        if 'savior' not in self.unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.unit, gameStateObj)
        self.other_unit.unrescue(gameStateObj)

    def reverse(self, gameStateObj):
        self.other_unit.TRV = self.unit.TRV
        self.other_unit.strTRV = self.unit.strTRV
        self.unit.hasTraded = self.hasTraded
        if 'savior' not in self.other_unit.status_bundle:
            StatusObject.HandleStatusAddition(StatusObject.statusparser("Rescue"), self.other_unit, gameStateObj)
        self.unit.unrescue(gameStateObj)

# === ITEM ACTIONS ==========================================================
class PutItemInConvoy(Action):
    def __init__(self, item):
        self.item = item

    def do(self, gameStateObj):
        gameStateObj.convoy.append(self.item)
        gameStateObj.banners.append(Banner.sent_to_convoyBanner(self.item))
        gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        gameStateObj.convoy.append(self.item)

    def reverse(self, gameStateObj):
        gameStateObj.convoy.remove(self.item)

class GiveItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.convoy = False

    def do(self, gameStateObj):
        if len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item)
            gameStateObj.banners.append(Banner.acquiredItemBanner(self.unit, self.item))
            gameStateObj.stateMachine.changeState('itemgain')
        elif self.unit.team == 'player':
            self.convoy = True
            gameStateObj.convoy.append(self.item)
            gameStateObj.banners.append(Banner.sent_to_convoyBanner(self.item))
            gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        if len(self.unit.items) < cf.CONSTANTS['max_items']:
            self.unit.add_item(self.item)
        elif self.unit.team == 'player':
            self.convoy = True
            gameStateObj.convoy.append(self.item)

    def reverse(self, gameStateObj):
        if self.convoy:
            self.convoy.remove(self.item)
        else:
            self.unit.remove_item(self.item)

class DropItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self, gameStateObj):
        self.item.droppable = False
        self.unit.add_item(self.item)
        gameStateObj.banners.append(Banner.acquiredItemBanner(self.unit, self.item))
        gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        self.item.droppable = False
        self.unit.add_item(self.item)

    def reverse(self, gameStateObj):
        self.item.droppable = True
        self.unit.remove_item(self.item)

class DiscardItem(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.item_index = self.unit.items.index(self.item)

    def do(self, gameStateObj):
        self.unit.remove_item(self.item)
        gameStateObj.convoy.append(self.item)

    def reverse(self, gameStateObj):
        gameStateObj.convoy.remove(self.item)
        self.unit.insert_item(self.item_index, self.item)

class RemoveItem(DiscardItem):
    def do(self, gameStateObj):
        self.unit.remove_item(self.item)

    def reverse(self, gameStateObj):
        self.unit.insert_item(self.item_index, self.item)

class EquipItem(Action):
    """
    Assumes item is already in invetory
    """
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item
        self.old_idx = self.unit.items.index(self.item)

    def do(self, gameStateObj):
        self.unit.equip(self.item)

    def reverse(self, gameStateObj):
        self.unit.insert_item(self.old_idx, self.item)

class TradeItem(Action):
    def __init__(self, unit1, unit2, item1, item2):
        self.unit1 = unit1
        self.unit2 = unit2
        self.item1 = item1
        self.item2 = item2
        self.item_index1 = unit1.items.index(item1) if item1 != "EmptySlot" else 4
        self.item_index2 = unit2.items.index(item2) if item2 != "EmptySlot" else 4
        self.hasTraded = self.unit1.hasTraded
        self.hasMoved = self.unit1.hasMoved
        # self.hasTraded2 = self.unit2.hasTraded

    def swap(self, unit1, unit2, item1, item2, item_index1, item_index2):
        # Do the swap
        if item1 and item1 is not "EmptySlot":
            unit1.remove_item(item1)
            unit2.insert_item(item_index2, item1)
        if item2 and item2 is not "EmptySlot":
            unit2.remove_item(item2)
            unit1.insert_item(item_index1, item2)   

    def do(self, gameStateObj):
        self.swap(self.unit1, self.unit2, self.item1, self.item2, self.item_index1, self.item_index2)
        self.unit1.hasTraded = True
        # self.unit2.hasTraded = True
        self.unit1.hasMoved = True

    def reverse(self, gameStateObj):
        self.swap(self.unit1, self.unit2, self.item2, self.item1, self.item_index2, self.item_index1)
        self.unit1.hasTraded = self.hasTraded
        # self.unit2.hasTraded = self.hasTraded2
        self.unit1.hasMoved = self.hasMoved

class UseItem(Action):
    """
    Doesn't actually fully USE the item, just reduces the number of uses
    """
    def __init__(self, item):
        self.item = item

    def do(self, gameStateObj):
        if self.item.uses:
            self.item.uses.decrement()
        if self.item.c_uses:
            self.item.c_uses.decrement()

    def reverse(self, gameStateObj):
        if self.item.uses:
            self.item.uses.increment()
        if self.item.c_uses:
            self.item.c_uses.increment()

class GainExp(Action):
    def __init__(self, unit, exp, in_combat=None):
        self.unit = unit
        self.exp_amount = exp
        self.old_exp = self.unit.exp
        self.old_level = self.unit.level
        self.current_stats = [s.base_stat for s in self.unit.stats.values()]
        self.levelup_list = None

        self.promoted_to = None  # Determined on reverse
        self.current_class = self.unit.klass

        self.current_skills = [s.id for s in self.unit.status_effects]
        self.added_skills = []  # Determined on reverse

        self.in_combat = in_combat

    def _forward_class_change(self, gameStateObj, promote=True):
        old_klass = gameStateObj.metaDataObj['class_dict'][self.current_class]
        new_klass = gameStateObj.metaDataObj['class_dict'][self.promoted_to]
        self.unit.leave(gameStateObj)
        self.unit.klass = self.promoted_to
        self.unit.removeSprites()
        self.unit.loadSprites()
        if promote:
            self.unit.level = 1
            self.unit.set_exp(0)
            self.levelup_list = new_klass['promotion']
            for index, stat in enumerate(self.levelup_list):
                self.levelup_list[index] = min(stat, new_klass['max'][index] - self.current_stats[index])
            self.unit.apply_levelup(self.levelup_list)
            self.unit.increase_wexp(new_klass['wexp_gain'], gameStateObj, banner=False)
        self.unit.movement_group = new_klass['movement_group']
        # Handle tags
        if old_klass['tags']:
            self.unit.tags -= old_klass['tags']
        if new_klass['tags']:
            self.unit.tags |= new_klass['tags']
        self.unit.arrive(gameStateObj)

    def _reverse_class_change(self, gameStateObj, promote=True):
        old_klass = gameStateObj.metaDataObj['class_dict'][self.current_class]
        new_klass = gameStateObj.metaDataObj['class_dict'][self.promoted_to]
        self.unit.leave(gameStateObj)
        self.unit.klass = self.current_class
        self.unit.removeSprites()
        self.unit.loadSprites()
        if promote:
            self.unit.level = self.old_level
            self.unit.set_exp(self.old_exp)
            self.unit.apply_levelup([-x for x in self.levelup_list])
            self.unit.increase_wexp([-x for x in new_klass['wexp_gain']], gameStateObj, banner=False)
        self.unit.movement_group = old_klass['movement_group']
        # Handle tags
        if new_klass['tags']:
            self.unit.tags -= new_klass['tags']
        if old_klass['tags']:
            self.unit.tags |= old_klass['tags']
        self.unit.arrive(gameStateObj)

    def _add_skills(self, gameStateObj):
        # If we don't already have this skill
        for s_id in self.added_skills:
            skill = StatusObject.statusparser(s_id)
            if skill.stack or skill.id not in (s.id for s in self.unit.status_effects):
                StatusObject.HandleStatusAddition(skill, self.unit, gameStateObj)

    def _remove_skills(self, added_skills, gameStateObj):
        # If we don't already have this skill
        for skill in added_skills:
            StatusObject.HandleStatusRemoval(skill, self.unit, gameStateObj)
            self.added_skills.append(skill.id)

    def do(self, gameStateObj):
        gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.unit, exp=self.exp_amount, in_combat=self.in_combat))
        gameStateObj.stateMachine.changeState('expgain')
        self.in_combat = None  # Don't need this anymore

    def execute(self, gameStateObj):
        if self.exp_amount + self.unit.exp >= 100:
            klass_dict = gameStateObj.metaDataObj['class_dict'][self.unit.klass]
            max_level = klass_dict['max_level']
            # Level Up
            if self.unit.level >= max_level:
                if cf.CONSTANTS['auto_promote'] and klass_dict['turns_into']: # If has at least one class to turn into
                    self._forward_class_change(gameStateObj, True)
                else:
                    self.unit.set_exp(99)
            else:
                self.unit.set_exp((self.unit.exp + self.exp_amount)%100)
                self.unit.level += 1
                self.unit.apply_levelup(self.levelup_list)
            self._add_skills(gameStateObj)    
        else:
            self.unit.change_exp(self.exp_amount)

    def reverse(self, gameStateObj):
        self.promoted_to = self.unit.klass
        added_skills = [skill for skill in self.unit.status_effects if skill.id not in self.current_skills]
        if self.unit.exp < self.exp_amount: # Leveled up
            klass_dict = gameStateObj.metaDataObj['class_dict'][self.current_class]
            max_level = klass_dict['max_level']
            stats_after_levelup = [s.base_stat for s in self.unit.stats.values()]
            self.levelup_list = [a - b for a, b in zip(stats_after_levelup, self.current_stats)]
            if self.unit.level == 1:  # Promoted here
                self._reverse_class_change(gameStateObj, True)
            elif self.unit.level >= max_level and self.unit.exp >= 99:
                self.unit.set_exp(self.old_exp)
            else:
                self.unit.set_exp(100 - self.exp_amount + self.unit.exp)
                self.unit.level -= 1
                self.unit.apply_levelup([-x for x in self.levelup_list])
            self._remove_skills(added_skills, gameStateObj)
        else:
            self.unit.change_exp(-self.exp_amount)

class Promote(GainExp):
    def __init__(self, unit):
        self.unit = unit

        self.old_exp = self.unit.exp
        self.old_level = self.unit.level
        self.current_stats = [s.base_stat for s in self.unit.stats.values()]
        self.levelup_list = None

        self.promoted_to = None
        self.current_class = self.unit.klass

        self.current_skills = [s.id for s in self.unit.status_effects]
        self.added_skills = []  # Determined on reverse

    def do(self, gameStateObj):
        gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.unit, exp=0, force_promote=True))
        gameStateObj.stateMachine.changeState('expgain')

    def execute(self, gameStateObj):
        self._forward_class_change(gameStateObj, True)
        self._add_skills(gameStateObj)

    def reverse(self, gameStateObj):
        self.promoted_to = self.unit.klass
        added_skills = [skill for skill in self.unit.status_effects if skill.id not in self.current_skills]
        stats_after_levelup = [s.base_stat for s in self.unit.stats.values()]
        self.levelup_list = [a - b for a, b in zip(stats_after_levelup, self.current_stats)]
        self._reverse_class_change(gameStateObj, True)
        self._remove_skills(added_skills, gameStateObj)

class PermanentStatIncrease(Action):
    def __init__(self, unit, stat_increase):
        self.unit = unit
        self.current_stats = [stat.base_stat for stat in self.unit.stats.values()]
        self.stat_increase = stat_increase

    def do(self, gameStateObj):
        gameStateObj.levelUpScreen.append(LevelUp.levelUpScreen(gameStateObj, unit=self.unit, exp=0, force_level=self.stat_increase))
        gameStateObj.stateMachine.changeState('expgain')

    def execute(self, gameStateObj):
        klass = gameStateObj.metaDataObj['class_dict'][self.unit.klass]
        for index, stat in enumerate(self.stat_increase):
            self.stat_increase[index] = min(stat, klass['max'][index] - self.current_stats[index])
        self.unit.apply_levelup(self.stat_increase, True)

    def reverse(self, gameStateObj):
        for idx, stat in enumerate(self.unit.stats.values()):
            stat.base_stat = self.current_stats[idx]
        # Since hp_up...
        self.unit.change_hp(-self.stat_increase[0])

class GainWexp(Action):
    def __init__(self, unit, item):
        self.unit = unit
        self.item = item

    def do(self, gameStateObj):
        self.unit.increase_wexp(self.item, gameStateObj)

    def execute(self, gameStateObj):
        self.unit.increase_wexp(self.item, gameStateObj, banner=False)

    def reverse(self, gameStateObj):
        if isinstance(self.item, list):
            self.unit.increase_wexp([-x for x in self.item], gameStateObj, banner=False)
        else:
            change = -self.item.wexp if self.item.wexp else -1
            if self.item.TYPE in Weapons.TRIANGLE.name_to_index:
                self.unit.wexp[Weapons.TRIANGLE.name_to_index[self.item.TYPE]] += change

class ChangeHP(Action):
    def __init__(self, unit, num):
        self.unit = unit
        self.num = num
        self.old_hp = self.unit.currenthp

    def do(self, gameStateObj=None):
        self.unit.change_hp(self.num)

    def reverse(self, gameStateObj=None):
        self.unit.set_hp(self.old_hp)

class Miracle(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_hp = self.unit.currenthp

    def do(self, gameStateObj):
        self.unit.isDying = False
        self.unit.set_hp(1)
        miracle_status = None
        for status in self.unit.status_effects:
            if status.miracle and status.count and status.count.count > 0:
                status.count.count -= 1
                miracle_status = status
                break
        gameStateObj.banners.append(Banner.miracleBanner(self.unit, miracle_status))
        gameStateObj.stateMachine.changeState('itemgain')
        self.unit.sprite.change_state('normal', gameStateObj)

    def execute(self, gameStateObj):
        self.unit.isDying = False
        self.unit.set_hp(1)
        for status in self.unit.status_effects:
            if status.miracle and status.count and status.count.count > 0:
                status.count.count -= 1
                break

    def reverse(self, gameStateObj):
        # self.unit.isDying = True
        self.unit.set_hp(self.old_hp)
        for status in self.unit.status_effects:
            if status.miracle and status.count:
                status.count.count += 1
                break

class Die(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_pos = unit.position

        self.drop_action = None

    def do(self, gameStateObj):
        # Drop any travelers
        if self.unit.TRV:
            drop_me = gameStateObj.get_unit_from_id(self.unit.TRV)
            self.drop_action = Drop(self.unit, drop_me, self.unit.position)
            self.drop_action.do(gameStateObj)

        # I no longer have a position
        self.unit.leave(gameStateObj)
        self.unit.remove_from_map(gameStateObj)
        self.unit.position = None
        ##
        self.unit.dead = True
        self.unit.isDying = False

    def reverse(self, gameStateObj):
        self.unit.dead = False
        self.unit.sprite.set_transition('normal')
        self.unit.sprite.change_state('normal', gameStateObj)

        self.unit.position = self.old_pos
        self.unit.place_on_map(gameStateObj)
        self.unit.arrive(gameStateObj)

        if self.drop_action:
            self.drop_action.reverse(gameStateObj)

class Resurrect(Action):
    def __init__(self, unit):
        self.unit = unit

    def do(self, gameStateObj):
        self.unit.dead = False

    def reverse(self, gameStateObj):
        self.unit.dead = True

# === GENERAL ACTIONS =========================================================
class ChangeTeam(Action):
    def __init__(self, unit, new_team):
        self.unit = unit
        self.new_team = new_team
        self.old_team = self.unit.team
        self.reset_action = Reset(self.unit)

    def _change_team(self, team, gameStateObj):
        self.unit.leave(gameStateObj)
        self.unit.team = team
        gameStateObj.boundary_manager.reset_unit(self.unit)
        self.unit.loadSprites()

    def do(self, gameStateObj):
        self._change_team(self.new_team, gameStateObj)
        self.reset_action.do(gameStateObj)
        self.unit.arrive(gameStateObj)
        
    def reverse(self, gameStateObj):
        self._change_team(self.old_team, gameStateObj)
        self.reset_action.reverse(gameStateObj)
        self.unit.arrive(gameStateObj)

class ChangeAI(Action):
    def __init__(self, unit, new_ai):
        self.unit = unit
        self.old_ai = self.unit.ai_descriptor
        self.new_ai = new_ai

    def do(self, gameStateObj):
        self.unit.ai_descriptor = self.new_ai
        self.unit.get_ai(self.new_ai)

    def reverse(self, gameStateObj):
        self.unit.ai_descriptor = self.old_ai
        self.unit.get_ai(self.old_ai)

class ChangeParty(Action):
    def __init__(self, unit, new_party):
        self.unit = unit
        self.old_party = self.unit.party
        self.new_party = new_party

    def do(self, gameStateObj):
        self.unit.party = self.new_party

    def reverse(self, gameStateObj):
        self.unit.party = self.old_party

class GiveGold(Action):
    def __init__(self, amount):
        self.amount = amount

    def do(self, gameStateObj):
        gameStateObj.game_constants['money'] += self.amount
        gameStateObj.banners.append(Banner.acquiredGoldBanner(self.amount))
        gameStateObj.stateMachine.changeState('itemgain')

    def execute(self, gameStateObj):
        gameStateObj.game_constants['money'] += self.amount

    def reverse(self, gameStateObj):
        gameStateObj.game_constants['money'] -= self.amount

class ChangeGameConstant(Action):
    def __init__(self, constant, new_value):
        self.constant = constant
        self.already_present = False
        self.old_value = None
        self.new_value = new_value

    def do(self, gameStateObj):
        self.already_present = self.constant in gameStateObj.game_constants
        self.old_value = gameStateObj.game_constants[self.constant]
        gameStateObj.game_constants[self.constant] = self.new_value

    def reverse(self, gameStateObj):
        gameStateObj.game_constants[self.constant] = self.old_value        
        if not self.already_present:
            del gameStateObj.game_constants[self.constant]

class ChangeLevelConstant(Action):
    def __init__(self, constant, new_value):
        self.constant = constant
        self.already_present = False
        self.old_value = None
        self.new_value = new_value

    def do(self, gameStateObj):
        self.present = self.constant in gameStateObj.level_constants
        self.old_value = gameStateObj.level_constants[self.constant]   
        gameStateObj.level_constants[self.constant] = self.new_value

    def reverse(self, gameStateObj):
        gameStateObj.level_constants[self.constant] = self.old_value
        if not self.already_present:
            del gameStateObj.level_constants[self.constant]

class IncrementTurn(Action):
    def __init__(self):
        pass

    def do(self, gameStateObj):
        gameStateObj.turncount += 1

    def reverse(self, gameStateObj):
        gameStateObj.turncount -= 1

class MarkPhase(Action):
    def __init__(self, phase_name):
        self.phase_name = phase_name

class LockTurnwheel(Action):
    def __init__(self, lock):
        self.lock = lock

class Message(Action):
    def __init__(self, message):
        self.message = message

class AddTag(Action):
    def __init__(self, unit, new_tag):
        self.unit = unit
        self.new_tag = new_tag
        self.already_present = new_tag in unit.tags

    def do(self, gameStateObj):
        if not self.already_present:
            self.unit.tags.add(self.new_tag)

    def reverse(self, gameStateObj):
        if not self.already_present:
            self.unit.tags.remove(self.new_tag)

class AddTalk(Action):
    def __init__(self, unit1, unit2):
        self.unit1 = unit1
        self.unit2 = unit2

    def do(self, gameStateObj):
        gameStateObj.talk_options.append((self.unit1, self.unit2))

    def reverse(self, gameStateObj):
        gameStateObj.talk_options.remove((self.unit1, self.unit2))

class RemoveTalk(Action):
    def __init__(self, unit1, unit2):
        self.unit1 = unit1
        self.unit2 = unit2

    def do(self, gameStateObj):
        gameStateObj.talk_options.remove((self.unit1, self.unit2))

    def reverse(self, gameStateObj):
        gameStateObj.talk_options.append((self.unit1, self.unit2))

class ChangeObjective(Action):
    def __init__(self, display_name=None, win_condition=None, loss_condition=None):
        self.display_name = display_name
        self.win_condition = win_condition
        self.loss_condition = loss_condition

    def do(self, gameStateObj):
        obj = gameStateObj.objective
        self.old_values = obj.display_name_string, obj.win_condition_string, obj.loss_condition_string
        if self.display_name:
            obj.display_name_string = self.display_name
        if self.win_condition:
            obj.win_condition_string = self.win_condition
        if self.loss_condition:
            obj.loss_condition_string = self.loss_condition

    def reverse(self, gameStateObj):
        obj = gameStateObj.objective
        if self.display_name:
            obj.display_name_string = self.old_values[0]
        if self.win_condition:
            obj.win_condition_string = self.old_values[1]
        if self.loss_condition:
            obj.loss_condition_string = self.old_values[2]

# === SUPPORT ACTIONS =======================================================
class IncrementSupportLevel(Action):
    def __init__(self, unit1_id, unit2_id):
        self.unit1_id = unit1_id
        self.unit2_id = unit2_id

    def do(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        edge.increment_support_level()

    def reverse(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        edge.support_level -= 1
        edge.support_levels_this_chapter -= 1

class SupportGain(Action):
    def __init__(self, unit1_id, unit2_id, gain):
        self.unit1_id = unit1_id
        self.unit2_id = unit2_id
        self.gain = gain

        self.current_value = 0
        self.value_added_this_chapter = 0

    def do(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        self.current_value = edge.current_value
        self.value_added_this_chapter = edge.value_added_this_chapter
        edge.increment(self.gain)     

    def reverse(self, gameStateObj):
        edge = gameStateObj.support.get_edge(self.unit1_id, self.unit2_id)
        edge.current_value = self.current_value
        edge.value_added_this_chapter = self.value_added_this_chapter

class HasAttacked(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_value = self.unit.hasAttacked

    def do(self, gameStateObj):
        self.unit.hasAttacked = True

    def reverse(self, gameStateObj):
        self.unit.hasAttacked = self.old_value

class HasTraded(Action):
    def __init__(self, unit):
        self.unit = unit
        self.old_value = self.unit.hasTraded

    def do(self, gameStateObj):
        self.unit.hasTraded = True

    def reverse(self, gameStateObj):
        self.unit.hasTraded = self.old_value

class UpdateUnitRecords(Action):
    def __init__(self, unit, record):
        self.unit = unit
        self.record = record  # damage, healing, kills

    def do(self, gameStateObj=None):
        self.unit.records['damage'] += self.record[0]
        self.unit.records['healing'] += self.record[1]
        self.unit.records['kills'] += self.record[2]

    def reverse(self, gameStateObj=None):
        self.unit.records['damage'] -= self.record[0]
        self.unit.records['healing'] -= self.record[1]
        self.unit.records['kills'] -= self.record[2]

class RecordRandomState(Action):
    run_on_load = True
    
    def __init__(self, old, new):
        self.old = old
        self.new = new

    def do(self, gameStateObj):
        pass

    def execute(self, gameStateObj):
        static_random.set_combat_random_state(self.new)

    def reverse(self, gameStateObj):
        static_random.set_combat_random_state(self.old)

# === SKILL AND STATUS ACTIONS ===================================================
class ApplyStatus(Action):
    def __init__(self, unit, status_obj):
        self.unit = unit
        self.status_obj = status_obj
        self.actually_added = True

    def do(self, gameStateObj):
        if not StatusObject.HandleStatusAddition(self.status_obj, self.unit, gameStateObj):
            self.actually_added = False

    def reverse(self, gameStateObj):
        if self.actually_added:
            StatusObject.HandleStatusRemoval(self.status_obj, self.unit, gameStateObj)

class RemoveStatus(Action):
    def __init__(self, unit, status_obj):
        self.unit = unit
        self.status_obj = status_obj
        # Do we have to worry about time?
        # Or is it automatically taken care of

    def do(self, gameStateObj):
        StatusObject.HandleStatusRemoval(self.status_obj, self.unit, gameStateObj)

    def reverse(self, gameStateObj):
        StatusObject.HandleStatusAddition(self.status_obj, self.unit, gameStateObj)

class ApplyStatChange(Action):
    def __init__(self, unit, stat_change):
        self.unit = unit
        self.stat_change = stat_change
        self.movement_left = self.unit.movement_left
        self.currenthp = self.unit.currenthp

    def do(self, gameStateObj):
        self.unit.apply_stat_change(self.stat_change)

    def reverse(self, gameStateObj):
        self.unit.apply_stat_change([-i for i in self.stat_change])
        self.unit.movement_left = self.movement_left
        self.unit.set_hp(self.currenthp)

class ChangeStatusCount(Action):
    def __init__(self, status, new_count):
        self.status = status
        self.old_count = status.count
        self.new_count = new_count

    def do(self, gameStateObj=None):
        self.status.count = self.new_count

    def reverse(self, gameStateObj=None):
        self.status.count = self.old_count

class DecrementStatusTime(Action):
    def __init__(self, status):
        self.status = status

    def do(self, gameStateObj=None):
        self.status.time.decrement()

    def reverse(self, gameStateObj=None):
        self.status.time.increment()

class ChargeAllSkills(Action):
    def __init__(self, unit, new_charge):
        self.unit = unit
        self.old_charge = []
        for status in self.unit.status_effects:
            if status.active:
                self.old_charge.append(status.active.current_charge)
            elif status.automatic:
                self.old_charge.append(status.automatic.current_charge)
            else:
                self.old_charge.append(0)
        self.new_charge = new_charge

    def do(self, gameStateObj=None):
        for status in self.unit.status_effects:
            if status.active:
                status.active.increase_charge(self.unit, self.new_charge)
            elif status.automatic:
                status.active.increase_charge(self.unit, self.new_charge)

    def reverse(self, gameStateObj=None):
        for idx, status in enumerate(self.unit.status_effects):
            if status.active:
                status.active.current_charge = self.old_charge[idx]
            elif status.automatic:
                status.automatic.current_charge = self.old_charge[idx]

class FinalizeActiveSkill(Action):
    def __init__(self, status, unit):
        self.status = status
        self.unit = unit
        self.old_charge = self.status.active.current_charge

    def do(self, gameStateObj):
        self.status.active.current_charge = 0
        # If no other active skills, can remove active skill charged
        if not any(skill.active and skill.active.required_charge > 0 and 
                   skill.active.current_charge >= skill.active.required_charge for skill in self.unit.status_effects):
            self.unit.tags.discard('ActiveSkillCharged')
        if self.status.active.mode == 'Attack':
            self.status.active.reverse_mod()

class FinalizeAutomaticSkill(Action):
    def __init__(self, status, unit):
        self.status = status
        self.unit = unit
        self.current_charge = status.automatic.current_charge

    def do(self, gameStateObj):
        self.s = StatusObject.statusparser(self.status.automatic.status)
        StatusObject.HandleStatusAddition(self.s, self.unit, gameStateObj)
        self.status.automatic.reset_charge()

    def reverse(self, gameStateObj):
        StatusObject.HandleStatusRemoval(self.s, self.unit, gameStateObj)
        self.status.automatic.current_charge = self.current_charge

class ShrugOff(Action):
    def __init__(self, status):
        self.status = status
        self.old_time = self.status.time.time_left

    def do(self, gameStateObj=None):
        self.status.time.time_left = 1

    def reverse(self, gameStateObj=None):
        self.status.time.time_left = self.old_time

# === TILE ACTIONS ========================================================
class ChangeTileSprite(Action):
    run_on_load = True

    def __init__(self, pos, sprite_name, size, transition):
        self.pos = pos
        self.sprite_name = sprite_name
        self.size = size
        self.transition = transition

        self.old_image_name = None

    def do(self, gameStateObj):
        self.old_image_name = gameStateObj.map.tile_sprites[self.pos].image_name
        gameStateObj.map.change_tile_sprites(self.pos, self.sprite_name, self.size, self.transition)

    def execute(self, gameStateObj):
        gameStateObj.map.change_tile_sprites(self.pos, self.sprite_name, self.size, None)

    def reverse(self, gameStateObj):
        if self.old_image_name:  # If it was previously another name
            gameStateObj.map.change_tile_sprites(self.pos, self.old_image_name, self.size, None)
        else:  # It was previously the default map
            gameStateObj.map.change_tile_sprites(self.pos, None, self.size, None)

class ReplaceTiles(Action):
    run_on_load = True

    def __init__(self, pos_list, terrain_id):
        self.pos_list = pos_list
        self.terrain_id = terrain_id

        self.old_ids = {}

    def do(self, gameStateObj):
        for position in self.pos_list:
            self.old_ids[position] = gameStateObj.map.tiles[position].tile_id
            gameStateObj.map.replace_tile(position, self.terrain_id, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        for position, tile_id in self.old_ids.items():
            gameStateObj.map.replace_tiles(position, tile_id, gameStateObj.grid_manager)

class AreaReplaceTiles(Action):
    run_on_load = True

    def __init__(self, top_left_coord, image_name):
        self.top_left_coord = top_left_coord
        self.image_name = image_name

        self.old_ids = {}
 
    def do(self, gameStateObj):
        image = gameStateObj.map.loose_tile_sprites[self.image_name] 
        width = image.get_width()
        height = image.get_height()
        for x in range(self.top_left_coord[0], self.top_left_coord[0] + width):
            for y in range(self.top_left_coord[1], self.top_left_coord[1] + height):
                self.old_ids[(x, y)] = gameStateObj.map.tiles[(x, y)].tile_id
        gameStateObj.map.area_replace(self.top_left_coord, self.image_name, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        for position, tile_id in self.old_ids.items():
            gameStateObj.map.replace_tiles(position, tile_id, gameStateObj.grid_manager)

class LayerTileSprite(Action):
    run_on_load = True

    def __init__(self, layer, coord, image_name):
        self.layer = layer
        self.coord = coord
        self.image_name = image_name

    def do(self, gameStateObj):
        gameStateObj.map.layer_tile_sprite(self.layer, self.coord, self.image_name)

    def reverse(self, gameStateObj):
        gameStateObj.map.layers[self.layer].remove(self.image_name, self.coord)

class LayerTerrain(Action):
    run_on_load = True

    def __init__(self, layer, coord, image_name):
        self.layer = layer
        self.coord = coord
        self.image_name = image_name

        self.old_terrain_ids = {}

    def do(self, gameStateObj):
        for position, tile in gameStateObj.map.terrain_layers[self.layer]._tiles.items():
            self.old_terrain_ids[position] = tile.tile_id
        gameStateObj.map.layer_terrain(self.layer, self.coord, self.image_name, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        terrain_layer = gameStateObj.map.terrain_layers[self.layer]
        terrain_layer.reset(self.old_terrain_ids)
        # Make sure this works right
        if terrain_layer.show:
            gameStateObj.map.true_tiles = None  # Reset tiles if we made changes while showing
            gameStateObj.map.true_opacity_map = None
            if gameStateObj.grid_manager:
                gameStateObj.map.handle_grid_manager_with_layer(self.layer, gameStateObj.grid_manager)

class ShowLayer(Action):
    run_on_load = True

    def __init__(self, layer, transition):
        self.layer = layer
        self.transition = transition

    def do(self, gameStateObj):
        gameStateObj.map.show_layer(self.layer, self.transition, gameStateObj.grid_manager)

    def execute(self, gameStateObj):
        gameStateObj.map.show_layer(self.layer, None, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        gameStateObj.map.hide_layer(self.layer, None, gameStateObj.grid_manager)

class HideLayer(Action):
    run_on_load = True

    def __init__(self, layer, transition):
        self.layer = layer
        self.transition = transition

    def do(self, gameStateObj):
        gameStateObj.map.hide_layer(self.layer, self.transition, gameStateObj.grid_manager)

    def execute(self, gameStateObj):
        gameStateObj.map.hide_layer(self.layer, None, gameStateObj.grid_manager)

    def reverse(self, gameStateObj):
        gameStateObj.map.show_layer(self.layer, None, gameStateObj.grid_manager)

class ClearLayer(Action):
    run_on_load = True

    # Assume layer is hidden !!!
    def __init__(self, layer):
        self.layer = layer

        self.old_sprites = []
        self.old_terrain_ids = {}

    def do(self, gameStateObj):
        for sprite in gameStateObj.map.layers[self.layer]:
            self.old_sprites.append((sprite.position, sprite.image_name))
        for position, tile in gameStateObj.map.terrain_layers[self.layer]._tiles.items():
            self.old_terrain_ids[position] = tile.tile_id
        gameStateObj.map.clear_layer(self.layer)

    def reverse(self, gameStateObj):
        for position, image_name in self.old_sprites:
            gameStateObj.map.layer_terrain(self.layer, position, image_name, gameStateObj.grid_manager)
        gameStateObj.map.terrain_layers[self.layer].reset(self.old_terrain_ids)

class AddTileProperty(Action):
    run_on_load = True

    def __init__(self, coord, tile_property):
        self.coord = coord
        self.tile_property = tile_property

    def do(self, gameStateObj):
        gameStateObj.map.add_tile_property(self.coord, self.tile_property)

    def reverse(self, gameStateObj):
        gameStateObj.map.remove_tile_property(self.coord, self.tile_property)

class RemoveTileProperty(Action):
    run_on_load = True

    def __init__(self, coord, tile_property):
        self.coord = coord
        self.tile_property = tile_property

    def do(self, gameStateObj):
        gameStateObj.map.remove_tile_property(self.coord, self.tile_property)

    def reverse(self, gameStateObj):
        gameStateObj.map.add_tile_property(self.coord, self.tile_property)

class AddWeather(Action):
    run_on_load = True

    def __init__(self, weather):
        self.weather = weather

    def do(self, gameStateObj):
        gameStateObj.map.add_weather(self.weather)

    def reverse(self, gameStateObj):
        gameStateObj.map.remove_weather(self.weather)

class RemoveWeather(Action):
    run_on_load = True

    def __init__(self, weather):
        self.weather = weather

    def do(self, gameStateObj):
        gameStateObj.map.remove_weather(self.weather)

    def reverse(self, gameStateObj):
        gameStateObj.map.add_weather(self.weather)

class AddGlobalStatus(Action):
    run_on_load = True

    def __init__(self, status):
        self.status = status

    def do(self, gameStateObj):
        gameStateObj.map.add_global_status(self.status, gameStateObj)

    def reverse(self, gameStateObj):
        gameStateObj.map.remove_global_status(self.status, gameStateObj)

class RemoveGlobalStatus(Action):
    run_on_load = True

    def __init__(self, status):
        self.status = status

    def do(self, gameStateObj):
        gameStateObj.map.remove_global_status(self.status, gameStateObj)

    def reverse(self, gameStateObj):
        gameStateObj.map.add_global_status(self.status, gameStateObj)

# === Master Functions for adding to action log ===
def do(action, gameStateObj):
    action.do(gameStateObj)
    gameStateObj.action_log.append(action)

def execute(action, gameStateObj):
    action.execute(gameStateObj)
    gameStateObj.action_log.append(action)

def reverse(action, gameStateObj):
    action.reverse(gameStateObj)
    gameStateObj.action_log.remove(action)