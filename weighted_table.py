import random
import json


class WeightedTable:
    def __init__(self, table=None, table_name=None):
        self.total_weight = 0
        self.table = {}
        if table is not None:
            if isinstance(table, dict):
                self.table = table
            elif isinstance(table, str):
                with open(table) as table_file:
                    table_data = json.load(table_file)
                    if table_name is None:
                        self.table = table_data
                    else:
                        self.table = table_data[table_name]
            for weight in self.table.values():
                self.total_weight += weight

    def add_table_entry(self, entry, weight):
        self.table[entry] = weight
        self.total_weight += weight

    def remove_table_entry(self, entry):
        weight = self.table.pop(entry, 0)
        self.total_weight -= weight

    def set_entry_weight(self, entry, weight):
        prev_weight = self.table[entry]
        self.table[entry] = weight
        self.total_weight += weight - prev_weight

    def roll(self):
        if self.total_weight <= 0:
            return None
        roll = random.randint(1, self.total_weight)
        for entry in self.table:
            roll -= self.table[entry]
            if roll <= 0:
                return entry
        return None

    def roll_reduction(self, reduction):
        # same as roll, but reduces the weight of that entry by the specified amount
        # makes identical rolls less likely
        entry = self.roll()
        new_weight = self.table[entry] - reduction
        if new_weight < 0:
            new_weight = 0
        self.set_entry_weight(entry, new_weight)
        return entry
