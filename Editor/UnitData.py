from collections import OrderedDict
import sys
from PyQt4 import QtGui, QtCore

sys.path.append('../')
import Code.configuration as cf
import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../'
import Code.GlobalConstants as GC

import Code.ItemMethods as ItemMethods
import Code.CustomObjects as CustomObjects

from Code.UnitObject import Stat
import Code.Utility as Utility

import DataImport
from DataImport import Data
import EditorUtilities, Faction, UnitDialogs
from CustomGUI import SignalList

class UnitData(object):
    def __init__(self):
        self.clear()

    def clear(self):
        self.units = []
        self.reinforcements = []  # Should always be sorted by pack and then by event_id
        self.factions = OrderedDict()
        self.load_player_characters = False

    def load(self, fp):
        self.clear()
        current_mode = '0123456789' # Defaults to all modes
        with open(fp) as data:
            unitcontent = data.readlines()
            for line in unitcontent:
                # Process each line that was in the level file.
                line = line.strip()
                # Skip empty or comment lines
                if not line or line.startswith('#'):
                    continue
                # Process line
                unitLine = line.split(';')
                current_mode = self.parse_unit_line(unitLine, current_mode)
        self.reinforcements = sorted(self.reinforcements, key=lambda x: (x.pack, x.event_id))  # First sort

    def get_unit_images(self):
        return {unit.position: EditorUtilities.create_image(unit.klass_image) if unit.klass_image else 
                EditorUtilities.create_image(Data.class_data[unit.klass].get_image(unit.team, unit.gender))
                for unit in self.units if unit.position}

    def get_reinforcement_images(self, pack):
        return {rein.position: EditorUtilities.create_image(rein.klass_image) if rein.klass_image else 
                EditorUtilities.create_image(Data.class_data[rein.klass].get_image(rein.team, rein.gender))
                for rein in self.reinforcements if rein.position and rein.pack == pack}

    def get_unit_from_pos(self, pos):
        for unit in self.units:
            if unit.position == pos:
                return unit
        #print('Could not find unit at %s, %s' % (pos[0], pos[1]))

    def get_rein_from_pos(self, pos, pack):
        for rein in self.reinforcements:
            if rein.position == pos and rein.pack == pack:
                return rein
        #print('Could not find unit at %s, %s' % (pos[0], pos[1]))

    def get_idx_from_pos(self, pos):
        for idx, unit in enumerate(self.units):
            if unit.position == pos:
                return idx
        #print('Could not find unit at %s, %s' % (pos[0], pos[1]))
        return -1

    def get_ridx_from_pos(self, pos, pack):
        for idx, rein in enumerate(self.reinforcements):
            if rein.position == pos and rein.pack == pack:
                return idx
        #print('Could not find unit at %s, %s' % (pos[0], pos[1]))
        return -1

    def get_unit_str(self, pos):
        for unit in self.units:
            if unit.position == pos:
                return unit.name + ': ' + unit.klass + ' ' + str(unit.level) + ' -- ' + ','.join([item.name for item in unit.items])
        return ''

    def get_reinforcement_str(self, pos, pack):
        for rein in self.reinforcements:
            if rein.position == pos and rein.pack == pack:
                return pack + '_' + rein.event_id + ': ' + rein.klass + ' ' + str(rein.level) + ' -- ' + ','.join([item.name for item in rein.items])
        return ''

    def parse_unit_line(self, unitLine, current_mode):
        if unitLine[0] == 'faction':
            self.factions[unitLine[1]] = Faction.Faction(unitLine[1], unitLine[2], unitLine[3], unitLine[4])
        elif unitLine[0] == 'mode':
            current_mode = unitLine[1]
        elif unitLine[0] == 'load_player_characters':
            self.load_player_characters = True
        else: # For now it just loads every unit, irrespective of mode
            # New Unit
            if unitLine[1] == "0":
                if len(unitLine) > 7:
                    self.create_unit_from_line(unitLine)
                else:
                    self.add_unit_from_line(unitLine)
            # Saved Unit
            elif unitLine[1] == "1":
                self.saved_unit_from_line(unitLine)
        return current_mode

    def add_unit_from_line(self, unitLine):
        assert len(unitLine) == 6, "unitLine %s must have length 6"%(unitLine)
        legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
                  'unit_id': unitLine[3], 'position': unitLine[4], 'ai': unitLine[5]}
        self.add_unit_from_legend(legend)

    def add_unit_from_legend(self, legend):
        cur_unit = Data.unit_data[legend['unit_id']]
        position = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None
        cur_unit.position = position
        cur_unit.ai = legend['ai']
        cur_unit.team = legend['team']
        if legend['event_id'] != "0": # unit does not start on board
            if '_' in legend['event_id']:
                cur_unit.pack, cur_unit.event_id = legend['event_id'].split('_')
            else:
                cur_unit.pack, cur_unit.event_id = 'None', legend['event_id']
            self.reinforcements.append(cur_unit)
        else: # Unit does start on board
            self.units.append(cur_unit)

    def add_unit(self, unit):
        self.units.append(unit)

    def add_reinforcement(self, rein):
        self.reinforcements.append(rein)
        self.reinforcements = sorted(self.reinforcements, key=lambda x: (x.pack, x.event_id))
        return self.reinforcements.index(rein)

    def remove_unit_from_idx(self, unit_idx):
        if self.units:
            self.units.pop(unit_idx)

    def remove_reinforcement_from_idx(self, rein_idx):
        if self.reinforcements:
            self.reinforcements.pop(rein_idx)

    def replace_unit(self, unit_idx, unit):
        if self.units:
            self.units.pop(unit_idx)
        self.units.insert(unit_idx, unit)

    def replace_reinforcement(self, rein_idx, rein):
        if self.reinforcements:
            self.reinforcements.pop(rein_idx)
        # self.reinforcements.insert(rein_idx, rein)
        self.reinforcements.append(rein)
        self.reinforcements = sorted(self.reinforcements, key=lambda x: (x.pack, x.event_id))
        return self.reinforcements.index(rein)        

    def saved_unit_from_line(self, unitLine):
        self.add_unit_from_line(unitLine)

    def create_unit_from_line(self, unitLine):
        assert len(unitLine) in [9, 10], "unitLine %s must have length 9 or 10 (if optional status)"%(unitLine)
        legend = {'team': unitLine[0], 'unit_type': unitLine[1], 'event_id': unitLine[2], 
                  'class': unitLine[3], 'level': unitLine[4], 'items': unitLine[5], 
                  'position': unitLine[6], 'ai': unitLine[7], 'faction': unitLine[8]}
        self.create_unit_from_legend(legend)

    def create_unit_from_legend(self, legend):
        GC.U_ID += 1

        u_i = {}
        u_i['id'] = GC.U_ID
        u_i['team'] = legend['team']
        u_i['event_id'] = legend['event_id'] if legend['event_id'] != "0" else None
        if legend['class'].endswith('F'):
            legend['class'] = legend['class'][:-1] # strip off the F
            u_i['gender'] = 5  # Default female gender is 5
        else:
            u_i['gender'] = 0  # Default male gender is 0
        classes = legend['class'].split(',')
        u_i['klass'] = classes[-1]
        # Give default previous class
        # default_previous_classes(u_i['klass'], classes, class_dict)

        u_i['level'] = int(legend['level'])
        u_i['position'] = tuple([int(num) for num in legend['position'].split(',')]) if ',' in legend['position'] else None

        u_i['faction'] = legend['faction']
        faction = self.factions[u_i['faction']]
        u_i['name'] = faction.unit_name
        u_i['faction_icon'] = faction.faction_icon
        u_i['desc'] = faction.desc

        stats, u_i['growths'], u_i['growth_points'], u_i['items'], u_i['wexp'] = \
            self.get_unit_info(Data.class_dict, u_i['klass'], u_i['level'], legend['items'])
        u_i['stats'] = self.build_stat_dict(stats)
        
        u_i['tags'] = Data.class_dict[u_i['klass']]['tags']
        if '_' in legend['ai']:
            u_i['ai'], u_i['ai_group'] = legend['ai'].split('_')
        else:
            u_i['ai'], u_i['ai_group'] = legend['ai'], None
        u_i['movement_group'] = Data.class_dict[u_i['klass']]['movement_group']
        u_i['skills'] = []
        u_i['generic'] = True

        cur_unit = DataImport.Unit(u_i)

        # Reposition units
        cur_unit.position = u_i['position']
        if u_i['event_id']: # Unit does not start on board
            self.reinforcements.append(cur_unit)
        else: # Unit does start on board
            self.units.append(cur_unit)

        # Status Effects and Skills
        # get_skills(class_dict, cur_unit, classes, u_i['level'], gameStateObj, feat=False)

        # Extra Skills
        # if len(unitLine) == 10:
            # statuses = [StatusObject.statusparser(status) for status in unitLine[9].split(',')]
            # for status in statuses:
                # StatusObject.HandleStatusAddition(status, cur_unit, gameStateObj)

    def build_stat_dict(self, stats):
        st = OrderedDict()
        for idx, name in enumerate(cf.CONSTANTS['stat_names']):
            st[name] = Stat(idx, stats[idx])
        return st
    
    def get_unit_info(self, class_dict, klass, level, item_line):
        # Handle stats
        # hp, str, mag, skl, spd, lck, def, res, con, mov
        bases = class_dict[klass]['bases'][:] # Using copies    
        growths = class_dict[klass]['growths'][:] # Using copies

        # ignoring modify stats for now
        # bases = [sum(x) for x in zip(bases, gameStateObj.modify_stats['enemy_bases'])]
        # growths = [sum(x) for x in zip(growths, gameStateObj.modify_stats['enemy_growths'])]

        stats, growth_points = self.auto_level(bases, growths, level)
        # Make sure we don't exceed max
        stats = [Utility.clamp(stat, 0, class_dict[klass]['max'][index]) for index, stat in enumerate(stats)]

        # Handle items
        items = ItemMethods.itemparser(item_line)

        # Handle required wexp
        wexp = class_dict[klass]['wexp_gain'][:]
        # print(klass, wexp)
        for item in items:
            if item.weapon:
                weapon_types = item.TYPE
                item_level = item.weapon.LVL
            elif item.spell:
                weapon_types = item.TYPE
                item_level = item.spell.LVL
            else:
                continue
            for weapon_type in weapon_types:
                wexp_index = CustomObjects.WEAPON_TRIANGLE.type_to_index[weapon_type]
                item_requirement = CustomObjects.WEAPON_EXP.wexp_dict[item_level]
                # print(item, weapon_type, wexp_index, item_requirement, wexp[wexp_index])
                if item_requirement > wexp[wexp_index] and wexp[wexp_index] > 0:
                    wexp[wexp_index] = item_requirement
        # print(wexp)

        return stats, growths, growth_points, items, wexp

    def auto_level(self, bases, growths, level):
        # Only does fixed leveling
        stats = bases[:]
        growth_points = [50 for growth in growths]

        for index, growth in enumerate(growths):
            growth_sum = growth * (level - 1)
            stats[index] += growth_sum/100
            growth_points[index] += growth_sum%100

        return stats, growth_points

# This allows for drawing the units items to the right of the unit on the list menu
class ItemDelegate(QtGui.QStyledItemDelegate):
    def __init__(self, unit_data=None, rein=False):
        super(ItemDelegate, self).__init__()
        self.unit_data = unit_data
        self.rein = rein

    def paint(self, painter, option, index):
        super(ItemDelegate, self).paint(painter, option, index)
        if self.rein:
            current_unit = self.unit_data.reinforcements[index.row()]
        else:
            current_unit = self.unit_data.units[index.row()]
        for idx, item in enumerate(current_unit.items):
            image = Data.item_data[item.id].image
            rect = option.rect
            painter.drawImage(rect.right() - ((idx + 1) * 16), rect.center().y() - 8, EditorUtilities.create_image(image))

class UnitMenu(QtGui.QWidget):
    def __init__(self, unit_data, view, window):
        super(UnitMenu, self).__init__(window)
        self.grid = QtGui.QGridLayout()
        self.setLayout(self.grid)
        self.window = window
        self.view = view

        self.list = SignalList(self, del_func=self.remove_unit)
        self.list.setMinimumSize(128, 320)
        self.list.uniformItemSizes = True
        self.list.setIconSize(QtCore.QSize(32, 32))
        self.delegate = ItemDelegate(unit_data)
        self.list.setItemDelegate(self.delegate)

        self.load(unit_data)
        self.list.currentItemChanged.connect(self.center_on_unit)
        self.list.itemDoubleClicked.connect(self.modify_unit)
        # delete_key = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Delete), self.list)
        # self.connect(delete_key, QtCore.SIGNAL('activated()'), self.remove_unit)

        self.load_unit_button = QtGui.QPushButton('Load Unit')
        self.load_unit_button.clicked.connect(self.load_unit)
        self.create_unit_button = QtGui.QPushButton('Create Unit')
        self.create_unit_button.clicked.connect(self.create_unit)
        self.remove_unit_button = QtGui.QPushButton('Remove Unit')
        self.remove_unit_button.clicked.connect(self.remove_unit)

        self.grid.addWidget(self.list, 1, 0)
        self.grid.addWidget(self.load_unit_button, 2, 0)
        self.grid.addWidget(self.create_unit_button, 3, 0)
        self.grid.addWidget(self.remove_unit_button, 4, 0)

    # def trigger(self):
    #     self.view.tool = 'Units'

    def get_current_item(self):
        return self.list.item(self.list.currentRow())

    def get_current_unit(self):
        if self.unit_data.units:
            return self.unit_data.units[self.list.currentRow()]
        else:
            return None

    def get_item_from_unit(self, unit):
        return self.list.item(self.unit_data.units.index(unit))

    def set_current_idx(self, idx):
        self.list.setCurrentRow(idx)

    def center_on_unit(self, item, prev):
        idx = self.list.row(item)
        # idx = int(idx)
        unit = self.unit_data.units[idx]
        if unit.position:
            self.view.center_on_pos(unit.position)

    def load(self, unit_data):
        self.clear()
        self.unit_data = unit_data
        # Ingest Data
        for unit in self.unit_data.units:
            self.list.addItem(self.create_item(unit))

    def clear(self):
        self.list.clear()

    def create_item(self, unit):
        if unit.generic:
            item = QtGui.QListWidgetItem(str(unit.klass) + ': L' + str(unit.level))
        else:
            item = QtGui.QListWidgetItem(unit.name)
        klass = Data.class_data.get(unit.klass)
        if klass:
            item.setIcon(EditorUtilities.create_icon(klass.get_image(unit.team, unit.gender)))
        if not unit.position:
            item.setTextColor(QtGui.QColor("red"))
        return item

    def load_unit(self):
        loaded_unit, ok = UnitDialogs.LoadUnitDialog.getUnit(self, "Load Unit", "Select unit:")
        if ok:
            self.add_unit(loaded_unit)
            self.unit_data.add_unit(loaded_unit)
            self.window.update_view()

    def create_unit(self):
        created_unit, ok = UnitDialogs.CreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:")
        if ok:
            self.add_unit(created_unit)
            self.unit_data.add_unit(created_unit)
            self.window.update_view()

    def remove_unit(self):
        unit_idx = self.list.currentRow()
        self.list.takeItem(unit_idx)
        self.unit_data.remove_unit_from_idx(unit_idx)
        self.window.update_view()

    def modify_unit(self, item):
        idx = self.list.row(item)
        unit = self.unit_data.units[idx]
        if unit.generic:
            modified_unit, ok = UnitDialogs.CreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:", unit)
        else:
            modified_unit, ok = UnitDialogs.LoadUnitDialog.getUnit(self, "Load Unit", "Select unit:", unit)
        if ok:
            modified_unit.position = unit.position
            # Replace unit
            self.list.takeItem(idx)
            self.list.insertItem(idx, self.create_item(modified_unit))
            self.unit_data.replace_unit(idx, modified_unit)
            self.window.update_view()

    def add_unit(self, unit):
        self.list.addItem(self.create_item(unit))
        self.list.setCurrentRow(self.list.count() - 1)

    def tick(self, current_time):
        if GC.PASSIVESPRITECOUNTER.update(current_time):
            for idx, unit in enumerate(self.unit_data.units):
                klass = Data.class_data[unit.klass]
                klass_image = klass.get_image(unit.team, unit.gender)
                self.list.item(idx).setIcon(EditorUtilities.create_icon(klass_image))
                unit.klass_image = klass_image

class ReinforcementMenu(UnitMenu):
    def __init__(self, unit_data, view, window):
        UnitMenu.__init__(self, unit_data, view, window)
        self.delegate = ItemDelegate(unit_data, rein=True)
        self.list.setItemDelegate(self.delegate)

        self.pack_view_label = QtGui.QLabel("Group to display:")
        self.pack_view_combobox = QtGui.QComboBox()
        self.packs = []

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.pack_view_label)
        hbox.addWidget(self.pack_view_combobox)
        self.grid.addLayout(hbox, 0, 0)

        self.list.setSortingEnabled(True)

    # def trigger(self):
    #     self.view.tool = 'Reinforcements'

    def get_current_unit(self):
        if self.unit_data.reinforcements:
            return self.unit_data.reinforcements[self.list.currentRow()]
        else:
            return None

    def get_item_from_unit(self, unit):
        return self.list.item(self.unit_data.reinforcements.index(unit))

    def center_on_unit(self, item, prev):
        idx = self.list.row(item)
        # idx = int(idx)
        unit = self.unit_data.reinforcements[idx]
        if unit.position:
            EditorUtilities.setComboBox(self.pack_view_combobox, unit.pack)
            self.view.center_on_pos(unit.position)

    def current_pack(self):
        return self.pack_view_combobox.currentText()

    def load(self, unit_data):
        self.clear()
        self.unit_data = unit_data
        # Ingest Data
        for unit in self.unit_data.reinforcements:
            self.list.addItem(self.create_item(unit))

    def create_item(self, unit):
        if unit.generic:
            item = QtGui.QListWidgetItem(unit.pack + ': ' + unit.event_id + ' -- L' + str(unit.level))
        else:
            item = QtGui.QListWidgetItem(unit.pack + ': ' + unit.event_id + ' -- ' + unit.name)
        klass = Data.class_data.get(unit.klass)
        if klass:
            item.setIcon(EditorUtilities.create_icon(klass.get_image(unit.team, unit.gender)))
        if not unit.position:
            item.setTextColor(QtGui.QColor("red"))
        if unit.pack not in self.packs:
            self.packs.append(unit.pack)
            self.pack_view_combobox.addItem(unit.pack)
            self.pack_view_combobox.setCurrentIndex(self.pack_view_combobox.count() - 1)
        return item

    def load_unit(self):
        loaded_unit, ok = UnitDialogs.ReinLoadUnitDialog.getUnit(self, "Load Unit", "Select unit:")
        if ok:
            self.add_unit(loaded_unit)
            self.unit_data.add_reinforcement(loaded_unit)
            self.window.update_view()

    def create_unit(self):
        created_unit, ok = UnitDialogs.ReinCreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:")
        if ok:
            self.add_unit(created_unit)
            self.unit_data.add_reinforcement(created_unit)
            self.window.update_view()

    def remove_unit(self):
        unit_idx = self.list.currentRow()
        self.list.takeItem(unit_idx)
        unit = self.unit_data.reinforcements[unit_idx]
        self.check_remove_pack(unit)
        self.unit_data.remove_reinforcement_from_idx(unit_idx)
        self.window.update_view()

    def check_remove_pack(self, unit):
        if unit.pack:
            for rein in self.unit_data.reinforcements:
                if unit.pack == rein.pack:
                    break
            else:
                # Remove pack from pack combo
                self.pack_view_combobox.removeItem(unit.pack)

    def modify_unit(self, item):
        idx = self.list.row(item)
        unit = self.unit_data.reinforcements[idx]
        if unit.generic:
            modified_unit, ok = UnitDialogs.ReinCreateUnitDialog.getUnit(self, "Create Unit", "Enter values for unit:", unit)
        else:
            modified_unit, ok = UnitDialogs.ReinLoadUnitDialog.getUnit(self, "Load Unit", "Select unit:", unit)
        if ok:
            modified_unit.position = unit.position
            # Replace unit
            self.list.takeItem(idx)
            self.check_remove_pack(unit)
            item = self.create_item(modified_unit)
            self.list.insertItem(idx, item)
            self.list.setCurrentRow(self.list.row(item))
            self.unit_data.replace_reinforcement(idx, modified_unit)
            print(idx, self.list.row(item))
            self.window.update_view()

    def add_unit(self, unit):
        item = self.create_item(unit)
        self.list.addItem(item)
        self.list.setCurrentRow(self.list.row(item))

    def tick(self, current_time):
        if GC.PASSIVESPRITECOUNTER.update(current_time):
            for idx, unit in enumerate(self.unit_data.reinforcements):
                klass = Data.class_data[unit.klass]
                klass_image = klass.get_image(unit.team, unit.gender)
                self.list.item(idx).setIcon(EditorUtilities.create_icon(klass_image))
                unit.klass_image = klass_image