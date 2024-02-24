from Monsters import *
from Upgrades import *
from Spells import *
from Level import *
from Shrines import *
from CommonContent import *
from RiftWizard import *

import math, random, sys

def fix_earth_elemental(unit):
    unit.tags = [Tags.Elemental, Tags.Nature]
    unit.resists[Tags.Poison] = 100

def fix_hallowed_earth_elemental(unit):
    unit.tags = [Tags.Elemental, Tags.Nature, Tags.Holy]
    unit.resists[Tags.Poison] = 100

import mods.Bugfixes.Bugfixes
bugged_units_fixer = mods.Bugfixes.Bugfixes.bugged_units_fixer
bugged_units_fixer["Earth Elemental"] = fix_earth_elemental
bugged_units_fixer["Hallowed Earth Elemental"] = fix_hallowed_earth_elemental

curr_module = sys.modules[__name__]

def is_immune(target, source, damage_type, already_checked):

    if target.resists[damage_type] < 100:
        return False
    if source.owner and source.owner.team != TEAM_PLAYER:
        return True
    
    # Calculate redeals for minions

    if isinstance(source, Spell) and hasattr(source, "can_redeal") and (source, target) not in already_checked:
        already_checked.append((source, target))
        if source.can_redeal(target, already_checked):
            return False
    
    for buff in target.level.player_unit.buffs:
        if not isinstance(buff, Upgrade):
            continue
        # Unconditional redeal skills
        if damage_type in buff.conversions:
            for redeal_type in buff.conversions[damage_type]:
                # Assume there are no chained or cyclical redeals when minions are concerned
                if target.resists[redeal_type] < 100:
                    return False
        # Unconditional redeal shrines are all non-conjuration so we don't need to worry about them

    # Conditional redeal effects
    if not hasattr(target.level, "conditional_redeals"):
        return True
    for buff in target.level.conditional_redeals:
        if (buff, target, source, damage_type) in already_checked:
            continue
        already_checked.append((buff, target, source, damage_type))
        if buff.can_redeal(target, source, damage_type, already_checked):
            return False
    
    return True

def is_conj_skill_summon(unit):
    return unit.source and isinstance(unit.source, Upgrade) and unit.source.tags and Tags.Conjuration in unit.source.tags

class FloatingEyeBuff(Buff):

    def __init__(self, spell):
        self.spell = spell
        Buff.__init__(self)
    
    def on_applied(self, owner):
        for spell in self.spell.caster.spells:
            if Tags.Eye not in spell.tags:
                continue
            spell_copy = type(spell)()
            spell_copy.caster = self.owner
            spell_copy.owner = self.owner
            spell_copy.statholder = self.spell.caster
            if not spell_copy.can_cast(self.owner.x, self.owner.y):
                continue
            self.spell.caster.level.act_cast(self.owner, spell_copy, self.owner.x, self.owner.y, pay_costs=False)

def modify_class(cls):

    if cls is SlimeBuff:

        def on_applied(self, owner):
            self.start_hp = self.owner.max_hp
            self.to_split = self.start_hp * 2
            self.growth = self.start_hp / 10
            self.gr_integer = math.floor(self.growth)
            self.gr_remainder = self.growth - self.gr_integer
            if self.gr_remainder > 0:
                self.description = "50%% chance to gain HP and max HP per turn. The amount gained has a %d%% chance to be %d and %d%% chance to be %d. Upon reaching %d HP, splits into 2 %s." % (round(self.gr_remainder*100), self.gr_integer + 1, round((1 - self.gr_remainder)*100), self.gr_integer, self.to_split, self.spawner_name)
            else:
                self.description = "50%% chance to gain %d HP and max HP per turn.  Upon reaching %d HP, splits into 2 %s." % (self.growth, self.to_split, self.spawner_name)

        def on_advance(self):
            if random.random() >= .5:
                remainder_chance = random.random()
                if self.owner.cur_hp == self.owner.max_hp:
                    self.owner.max_hp += self.gr_integer
                    if self.gr_remainder > 0 and remainder_chance < self.gr_remainder:
                        self.owner.max_hp += 1
                self.owner.deal_damage(-self.gr_integer, Tags.Heal, self)
                if self.gr_remainder > 0 and remainder_chance < self.gr_remainder:
                    self.owner.deal_damage(-1, Tags.Heal, self)

            if self.owner.cur_hp < self.to_split:
                return
            
            single = self.to_split//2
            while self.owner.max_hp >= self.to_split:
                p = self.owner.level.get_summon_point(self.owner.x, self.owner.y)
                if not p:
                    return
                self.owner.max_hp -= single
                self.owner.cur_hp = self.owner.max_hp
                unit = self.spawner()
                unit.team = self.owner.team
                if not unit.source:
                    unit.source = self.owner.source
                self.owner.level.add_obj(unit, p.x, p.y)

    if cls is HallowFlesh:

        def get_impacted_tiles(self, x, y):
            candidates = set([Point(x, y)])
            unit_group = set()

            while candidates:
                candidate = candidates.pop()
                unit = self.caster.level.get_unit_at(candidate.x, candidate.y)
                if unit and unit not in unit_group:
                    if unit is self.caster:
                        continue
                    unit_group.add(unit)

                    for p in self.caster.level.get_adjacent_points(Point(unit.x, unit.y), filter_walkable=False):
                        candidates.add(p)
                    
            return list(unit_group)

    if cls is MeltSpell:

        def on_init(self):
            self.tags = [Tags.Fire, Tags.Sorcery]
            self.level = 2
            self.max_charges = 15
            self.name = "Melt"
            self.damage = 22
            self.element = Tags.Fire
            self.range = 6

            self.can_target_empty = False

            self.upgrades['damage'] = (16, 2)
            self.upgrades['max_charges'] = 10
            self.upgrades['ice_resist'] = (1, 3, "Ice Penetration", "Melt also reduces [ice] resist by 100")

        def cast_instant(self, x, y):
            self.caster.level.deal_damage(x, y, self.get_stat('damage'), self.element, self)
            unit = self.caster.level.get_unit_at(x, y)
            if unit:
                unit.apply_buff(MeltBuff(self))

    if cls is MeltBuff:

        def on_init(self):
            self.resists[Tags.Physical] = -100
            if self.spell.get_stat('ice_resist'):
                self.resists[Tags.Ice] = -100
            self.stack_type = STACK_REPLACE
            self.color = Color(255, 100, 100)
            self.name = "Melted"
            self.buff_type = BUFF_TYPE_CURSE

    if cls is Buff:

        def subscribe(self):
            event_manager = self.owner.level.event_manager

            for event_type, trigger in self.owner_triggers.items():
                event_manager.register_entity_trigger(event_type, self.owner, trigger)
            for event_type, trigger in self.global_triggers.items():
                event_manager.register_global_trigger(event_type, trigger)
            
            if not hasattr(self.owner.level, "conditional_redeals"):
                self.owner.level.conditional_redeals = []
            if hasattr(self, "can_redeal"):
                self.owner.level.conditional_redeals.append(self)

        def unsubscribe(self):
            event_manager = self.owner.level.event_manager
            
            for event_type, trigger in self.owner_triggers.items():
                event_manager.unregister_entity_trigger(event_type, self.owner, trigger)
            for event_type, trigger in self.global_triggers.items():
                event_manager.unregister_global_trigger(event_type, trigger)
            
            if hasattr(self.owner.level, "conditional_redeals") and self in self.owner.level.conditional_redeals:
                self.owner.level.conditional_redeals.remove(self)

        def process_conversions(self, evt): 
            # Do not deal damage to dead units
            if not evt.unit.is_alive():
                return
            # Do not deal damage to friendly units
            if not are_hostile(self.owner, evt.unit):
                return

            if evt.damage_type in self.conversions and are_hostile(self.owner, evt.unit):
                for dest_dtype, mult in self.conversions[evt.damage_type].items():
                    self.owner.level.queue_spell(self.deal_conversion_damage(evt, mult, dest_dtype))

            sources = [evt.source]

            for source in sources:
                # Spell conversions only convert damage from the owner's spells (or minions)
                if source.owner is not self.owner:
                    continue

                if type(source) in self.spell_conversions:
                    if evt.damage_type in self.spell_conversions[type(source)]:
                        for dest_dtype, mult in self.spell_conversions[type(source)][evt.damage_type].items():
                            self.owner.level.queue_spell(self.deal_conversion_damage(evt, mult, dest_dtype))

    if cls is RedStarShrineBuff:

        def on_init(self):
            self.global_triggers[EventOnPreDamaged] = self.on_damage
            self.can_redeal = lambda u, source, damage_type, already_checked: can_redeal(self, u, source, damage_type, already_checked)

        def can_redeal(self, u, source, damage_type, already_checked):
            return source.owner and isinstance(source.owner.source, self.spell_class) and (Tags.Arcane in u.tags or Tags.Dark in u.tags or Tags.Fire in u.tags) and not is_immune(u, self, Tags.Holy, already_checked)

    if cls is Spell:

        def get_ai_target(self):
            if self.self_target:
                return self.caster if self.can_cast(self.caster.x, self.caster.y) else None

            if hasattr(self, "radius") and self.radius > 0:
                return self.get_corner_target(self.get_stat("radius"))

            def is_good_target(u):    
                if not u:
                    return False
                if bool(self.target_allies) == bool(self.caster.level.are_hostile(u, self.caster)):
                    return False
                if hasattr(self, 'damage_type') and not self.level:
                    if isinstance(self.damage_type, list):
                        if all(is_immune(u, self, dtype, []) for dtype in self.damage_type):
                            return False
                    else:
                        if is_immune(u, self, self.damage_type, []):
                            return False
                if not self.can_cast(u.x, u.y):
                    return False
                return True

            targets = [u for u in self.caster.level.units if is_good_target(u)]
            if not self.target_allies:
                targets = [target for target in targets if not target.has_buff(Soulbound) or target.cur_hp > 1]
            if not targets:
                return None
            else:
                target = random.choice(targets)
                return Point(target.x, target.y)

        def get_corner_target(self, radius, requires_los=True):
            # Find targets possibly around corners
            # Returns the first randomly found target which will hit atleast one enemy with a splash of the given radius

            dtypes = []
            if hasattr(self, 'damage_type'):
                if isinstance(self.damage_type, Tag):
                    dtypes = [self.damage_type]
                else:
                    dtypes = self.damage_type
            
            def is_target(v):
                if bool(self.target_allies) == bool(are_hostile(v, self.caster)):
                    return False
                # if no damage type is specified, take any hostile target
                if not dtypes:
                    return True
                for dtype in dtypes:
                    if not is_immune(v, self, dtype, []):
                        return True

            nearby_enemies = self.caster.level.get_units_in_ball(self.caster, self.get_stat("range") + radius)
            nearby_enemies = [u for u in nearby_enemies if is_target(u)]

            possible_cast_points = list(self.caster.level.get_points_in_ball(self.caster.x, self.caster.y, self.get_stat("range")))

            # Filter points that are not close to any enemies
            potentials = []
            for p in possible_cast_points:
                for e in nearby_enemies:
                    if distance(p, e, diag=False, euclidean=False) < radius:
                        potentials.append(p)
                        break

            possible_cast_points = potentials

            # Filter points that the spell cannot target
            potentials = []
            for p in possible_cast_points:
                if self.can_cast(p.x, p.y):
                    potentials.append(p)

            possible_cast_points = potentials
            random.shuffle(possible_cast_points)

            def can_hit(p, u):
                return distance(p, u, diag=False, euclidean=False) <= radius and (not self.get_stat("requires_los") or self.caster.level.can_see(p.x, p.y, u.x, u.y))

            for p in possible_cast_points:
                if not any(is_target(u) and can_hit(p, u) for u in self.owner.level.get_units_in_ball(p, radius)):
                    continue
                return p
            return None

    if cls is Unit:

        def can_harm(self, other):
            if other.has_buff(Soulbound) and other.cur_hp == 1:
                return False
            for s in self.spells:
                if not hasattr(s, 'damage_type'):
                    return True
                if isinstance(s.damage_type, list):
                    for d in s.damage_type:
                        if not is_immune(other, s, d, []):
                            return True
                else:
                    if not is_immune(other, s, s.damage_type, []):
                        return True
            return False

    if cls is ElementalClawBuff:

        def on_init(self):
            self.global_triggers[EventOnPreDamaged] = self.on_damage
            self.dtype = None
            self.can_redeal = lambda u, source, damage_type, already_checked: can_redeal(self, u, source, damage_type, already_checked)

        def can_redeal(self, u, source, damage_type, already_checked):
            return damage_type == Tags.Physical and source.owner and isinstance(source.owner.source, self.spell_class) and not is_immune(u, self, self.dtype, already_checked)

    if cls is LightningSpireArc:

        def can_target(self, t):
            if not are_hostile(self.owner, t):
                return False
            if not self.get_stat('resistance_debuff') and is_immune(t, self, Tags.Lightning, []):
                return False
            if not self.owner.level.can_see(self.owner.x, self.owner.y, t.x, t.y):
                return self.get_stat('requires_los')
            return True

    if cls is Houndlord:

        def on_unit_added(self, evt):

            if evt.unit is not self.owner:
                return

            for p in self.owner.level.get_adjacent_points(self.owner, check_unit=False):
                existing = self.owner.level.tiles[p.x][p.y].unit

                if existing:
                    if not is_conj_skill_summon(existing):
                        continue
                    p = self.owner.level.get_summon_point(self.owner.x, self.owner.y)

                unit = HellHound()
                
                for s in unit.spells:
                    s.damage = self.get_stat('minion_damage')

                unit.spells[1].range = self.get_stat('minion_range')
                unit.max_hp = self.get_stat('minion_health')
                
                self.summon(unit, p)

    if cls is SummonArchon:

        def cast_instant(self, x, y):

            angel = Unit()
            angel.name = "Archon"
            angel.tags = [Tags.Holy, Tags.Lightning]
            
            angel.sprite.char ='A'
            angel.sprite.color = Tags.Holy.color

            angel.max_hp = self.get_stat('minion_health')
            angel.shields = self.get_stat('shields')

            angel.resists[Tags.Holy] = 100
            angel.resists[Tags.Dark] = 75
            angel.resists[Tags.Lightning] = 75

            lightning = ArchonLightning()
            lightning.damage = self.get_stat('minion_damage')
            lightning.range = self.get_stat('minion_range')
            angel.spells.append(lightning)
            angel.flying = True

            angel.turns_to_death = self.get_stat('minion_duration')

            self.summon(angel, Point(x, y))

    if cls is SummonSeraphim:

        def cast_instant(self, x, y):

            angel = Unit()
            angel.name = "Seraph"
            angel.asset_name = "seraphim"
            angel.tags = [Tags.Holy, Tags.Fire]

            angel.max_hp = self.get_stat('minion_health')
            angel.shields = self.get_stat('shields')

            angel.resists[Tags.Holy] = 100
            angel.resists[Tags.Dark] = 75
            angel.resists[Tags.Fire] = 75

            sword = SeraphimSwordSwing()
            sword.damage = self.get_stat('minion_damage')
            sword.all_damage_types = True
            if self.get_stat('moonblade'):
                sword.damage_type.append(Tags.Arcane)
            angel.spells.append(sword)
            angel.flying = True
            if self.get_stat('heal'):
                angel.buffs.append(HealAuraBuff(5, self.get_stat("radius", base=5)))

            if self.get_stat('essence'):
                aura = EssenceAuraBuff()
                aura.radius = self.get_stat("radius", base=5)
                angel.buffs.append(aura)

            if self.get_stat('holy_fire'):
                aura = DamageAuraBuff(damage=2, damage_type=[Tags.Fire, Tags.Holy], radius=self.get_stat("radius", base=5))
                angel.buffs.append(aura)

            angel.turns_to_death = self.get_stat('minion_duration')

            self.summon(angel, Point(x, y))

    if cls is SummonFloatingEye:

        def cast_instant(self, x, y):
            eye = FloatingEye()
            eye.spells = []
            eye.team = TEAM_PLAYER
            eye.max_hp += self.get_stat('minion_health')
            eye.turns_to_death = self.get_stat('minion_duration')
            eye.buffs.append(FloatingEyeBuff(self))

            p = self.caster.level.get_summon_point(x, y, flying=True)
            if p:
                # Ensure point exists before having the eye cast eye spells
                self.summon(eye, p)

    if cls is InvokeSavagerySpell:

        def cast(self, x, y):

            attack = SimpleMeleeAttack(damage=self.get_stat('damage'), buff=Stun, buff_duration=self.get_stat('duration'))

            for unit in self.caster.level.units:
                if unit == self.caster or are_hostile(self.caster, unit):
                    continue
                if Tags.Living not in unit.tags:
                    continue

                attack.statholder = unit
                attack.caster = unit
                attack.owner = unit
                possible_targets = [u for u in self.caster.level.get_units_in_ball(unit, radius=1, diag=True) if are_hostile(u, self.caster) and not is_immune(u, attack, attack.damage_type, [])]
                if possible_targets:
                    target = random.choice(possible_targets)
                    self.caster.level.act_cast(unit, attack, target.x, target.y, pay_costs=False)
                    yield

    if cls is ShrapnelBlast:

        def cast(self, x, y):
            target = Point(x, y)
        
            damage = self.get_stat('damage')

            for point in self.caster.level.get_adjacent_points(Point(x, y)):
                self.caster.level.deal_damage(point.x, point.y, damage, Tags.Fire, self)

            for i in range(2):
                yield

            for i in range(self.get_stat('num_targets')):
                possible_targets = list(self.caster.level.get_points_in_ball(x, y, self.get_stat('radius')))
                
                if not self.get_stat('puncture'):
                    possible_targets = [t for t in possible_targets if self.caster.level.can_see(x, y, t.x, t.y, light_walls=True)]

                if self.get_stat('homing'):

                    def can_home(t):
                        u = self.caster.level.get_unit_at(t.x, t.y)
                        if not u:
                            return False
                        return are_hostile(self.caster, u)

                    enemy_targets = [t for t in possible_targets if can_home(t)]
                    if enemy_targets:
                        possible_targets = enemy_targets

                if possible_targets:
                    target = random.choice(possible_targets)
                    self.caster.level.deal_damage(target.x, target.y, damage, Tags.Physical, self)
                    for i in range(2):
                        yield

            self.caster.level.make_floor(x, y)
            return

    if cls is Purestrike:

        def on_init(self):
            self.name = "Purestrike"
            self.tags = [Tags.Holy, Tags.Arcane]
            self.level = 5
            self.global_triggers[EventOnPreDamaged] = self.on_damage
            self.can_redeal = lambda unit, source, damage_type, already_checked: can_redeal(self, unit, source, damage_type, already_checked)

        def on_damage(self, evt):
            if evt.damage_type != Tags.Physical:
                return
            if not evt.source or not evt.source.owner:
                return
            if evt.source.owner.shields < 1:
                return
            if evt.damage < 2:
                return
            if not are_hostile(evt.unit, self.owner):
                return
            self.owner.level.queue_spell(self.do_conversion(evt))
        
        def can_redeal(self, u, source, damage_type, already_checked):
            return damage_type == Tags.Physical and source.owner and source.owner.shields > 0 and (not is_immune(u, self, Tags.Holy, already_checked) or not is_immune(u, self, Tags.Arcane, already_checked))

    if cls is GlassPetrifyBuff:

        def on_applied(self, owner):
            return PetrifyBuff.on_applied(self, owner)

    if cls is SummonKnights:

        def on_init(self):
            self.name = "Knightly Oath"
            self.level = 7
            self.tags = [Tags.Conjuration, Tags.Holy]

            self.minion_health = 90

            self.max_charges = 2
            self.minion_damage = 7
            
            self.range = 0
            
            # Purely for shrine bonuses
            self.minion_range = 6

            self.upgrades['void_court'] = (1, 5, "Void Court", "Summon only void knights.  Summon a void champion as well.", "court")
            self.upgrades['storm_court'] = (1, 5, "Storm Court","Summon only storm knights.  Summon a storm champion as well.", "court")
            self.upgrades['chaos_court'] = (1, 5, "Chaos Court", "Summon only chaos knights.  Summon a chaos champion as well.", "court")
            self.upgrades['max_charges'] = (1, 3)

        def cast(self, x, y):

            knights = [VoidKnight(), ChaosKnight(), StormKnight()]
            if self.get_stat('void_court'):
                knights = [Champion(VoidKnight()), VoidKnight(), VoidKnight(), VoidKnight()]
            if self.get_stat('storm_court'):
                knights = [Champion(StormKnight()), StormKnight(), StormKnight(), StormKnight()]
            if self.get_stat('chaos_court'):
                knights = [Champion(ChaosKnight()), ChaosKnight(), ChaosKnight(), ChaosKnight()]

            for u in knights:
                apply_minion_bonuses(self, u)
                u.buffs.append(KnightBuff(self.caster))
                self.summon(u)
                yield

    if cls is VoidBeamSpell:

        def cast(self, x, y):
            damage = self.get_stat('damage')
            for point in self.aoe(x, y):
                
                # Kill walls
                if not self.caster.level.tiles[point.x][point.y].can_see:
                    self.caster.level.make_floor(point.x, point.y)

                # Deal damage
                self.caster.level.deal_damage(point.x, point.y, damage, self.element, self)
            yield

    if cls is DamageAuraBuff:

        def on_advance(self):

            effects_left = 7

            for unit in self.owner.level.get_units_in_ball(Point(self.owner.x, self.owner.y), self.radius):
                if unit == self.owner:
                    continue

                if not self.friendly_fire and not self.owner.level.are_hostile(self.owner, unit):
                    continue

                if isinstance(self.damage_type, list):
                    damage_type = random.choice(self.damage_type)
                else:
                    damage_type = self.damage_type
                self.damage_dealt += unit.deal_damage(self.damage, damage_type, self.source or self)
                effects_left -= 1

            # Show some graphical indication of this aura if it didnt hit much
            points = self.owner.level.get_points_in_ball(self.owner.x, self.owner.y, self.radius)
            points = [p for p in points if not self.owner.level.get_unit_at(p.x, p.y)]
            random.shuffle(points)
            for i in range(effects_left):
                if not points:
                    break
                p = points.pop()
                if isinstance(self.damage_type, list):
                    damage_type = random.choice(self.damage_type)
                else:
                    damage_type = self.damage_type
                self.owner.level.deal_damage(p.x, p.y, 0, damage_type, source=self.source or self)

    if cls is VolcanoTurtleBuff:

        def on_init(self):
            self.description = ("Spews 3 meteors each turn at random locations within a radius of 6.\n\n"
                                "The meteors create explosions with 2 tiles radii, dealing 8 fire damage.\n\n"
                                "Tiles directly hit take 11 additional physical damage.\n\n"
                                "Enemies directly hit are stunned for 1 turn.")
            self.name = "Volcano Shell"

        def meteor(self, target):

            self.owner.level.deal_damage(target.x, target.y, 11, Tags.Physical, self)
            unit = self.owner.level.get_unit_at(target.x, target.y)
            if unit:
                unit.apply_buff(Stun(), 1)

            self.owner.level.show_effect(0, 0, Tags.Sound_Effect, 'hit_enemy')
            yield

            for stage in Burst(self.owner.level, target, 2, ignore_walls=True):
                for point in stage:
                    self.owner.level.deal_damage(point.x, point.y, 8, Tags.Fire, self)
                yield

    if cls is MordredCorruption:

        def cast(self, x, y):

            gen_params = self.caster.level.gen_params.make_child_generator(difficulty=self.forced_difficulty or self.caster.level.level_no)        
            gen_params.num_exits = self.num_exits
            gen_params.num_monsters = 25
            new_level = gen_params.make_level()

            # For the new level, pick some swaths of it.
            # For each tile in that swath, transport the tile and its contents to the new level
            # For units, remove then add them to make event subscriptions work...?
            chance = random.random() * .5 + .1
            targets = []

            num_portals = len(list(t for t in self.caster.level.iter_tiles() if isinstance(t.prop, Portal)))

            for i in range(len(new_level.tiles)):
                for j in range(len(new_level.tiles)):
                    if random.random() > chance:
                        if isinstance(self.caster.level.tiles[i][j].prop, Portal):
                            if num_portals <= 1:
                                continue
                            else:
                                num_portals -= 1
                        targets.append((i, j))
            random.shuffle(targets)

            for i, j in targets:
                
                old_unit = self.caster.level.get_unit_at(i, j)
                check = False
                if old_unit:
                    check = old_unit is self.caster or old_unit.is_player_controlled or old_unit.name == "Mordred"
                    check = check or is_conj_skill_summon(old_unit)
                if check:
                    continue
                elif old_unit:
                    old_unit.kill(trigger_death_event=False)

                new_tile = new_level.tiles[i][j]

                calc_glyph = random.choice([True, True, False])
                if new_tile.is_chasm:
                    self.caster.level.make_chasm(i, j, calc_glyph=calc_glyph)
                elif new_tile.is_floor():
                    self.caster.level.make_floor(i, j, calc_glyph=calc_glyph)
                else:
                    self.caster.level.make_wall(i, j, calc_glyph=calc_glyph)
                
                cur_tile = self.caster.level.tiles[i][j]                
                cur_tile.tileset = new_tile.tileset
                cur_tile.water = new_tile.water
                cur_tile.sprites = None

                unit = new_tile.unit
                if unit:
                    new_level.remove_obj(unit)
                if unit and not cur_tile.unit:
                    self.caster.level.add_obj(unit, i, j)

                prop = new_tile.prop
                if prop:
                    old_prop = cur_tile.prop
                    if old_prop:
                        self.caster.level.remove_prop(old_prop)
                    self.caster.level.add_prop(prop, i, j)

                # Remove props from chasms and walls
                if cur_tile.prop and not cur_tile.is_floor():
                    self.caster.level.remove_prop(cur_tile.prop)

                self.caster.level.show_effect(i, j, Tags.Translocation)

            self.caster.level.gen_params.ensure_connectivity()
            self.caster.level.gen_params.ensure_connectivity(chasm=True)
            self.caster.level.event_manager.raise_event(EventOnUnitPreAdded(self.caster), self.caster)
            self.caster.level.event_manager.raise_event(EventOnUnitAdded(self.caster), self.caster)
            yield

        def on_init(self):
            self.name = "Planar Interposition"
            self.description = "Mix the current realm with another.\nFriends and foes may be left behind; Mordred, the Wizard, and minions summoned by Conjuration skills will always remain."
            self.cool_down = 13
            self.range = 0
            self.num_exits = 0
            self.forced_difficulty = None

    if cls is Shrine:

        def get_buff(self, spell):
            buff = self.buff_class(spell, self)
            for (attr, amt) in self.attr_bonuses.items():
                if isinstance(amt, float):
                    if not hasattr(spell, attr):
                        continue
                    amt = math.ceil(getattr(spell, attr) * amt)
                buff.spell_bonuses[type(spell)][attr] = amt

            return buff

        def can_enhance(self, spell):
            if self.conj_only and Tags.Conjuration not in spell.tags:
                return False
            if self.no_conj and Tags.Conjuration in spell.tags and Tags.Sorcery not in spell.tags and Tags.Enchantment not in spell.tags:
                return False
            if self.tags and not any(t in self.tags for t in spell.tags):
                return False
            # Hacky- assume any shrine with a description has benefits beyond attr bonuses
            # Could also maybe check if buff class is ShrineBuff or no?
            if not self.description and self.attr_bonuses and not any(hasattr(spell, a) or not isinstance(amt, float) for (a, amt) in self.attr_bonuses.items()):
                return False
            return True

    if cls is PyGameView:

        def draw_examine_upgrade(self):
            path = ['UI', 'spell skill icons', self.examine_target.name.lower().replace(' ', '_') + '.png']
            self.draw_examine_icon()

            border_margin = self.border_margin
            cur_x = border_margin
            cur_y = border_margin

            width = self.examine_display.get_width() - 2 * border_margin
            lines = self.draw_wrapped_string(self.examine_target.name, self.examine_display, cur_x, cur_y, width=width)
            cur_y += self.linesize * (lines+1)

            # Draw upgrade tags
            if not getattr(self.examine_target, 'prereq', None) and hasattr(self.examine_target, 'tags'):
                for tag in Tags:
                    if tag not in self.examine_target.tags:
                        continue
                    self.draw_string(tag.name, self.examine_display, cur_x, cur_y, (tag.color.r, tag.color.g, tag.color.b))
                    cur_y += self.linesize
                cur_y += self.linesize

            if getattr(self.examine_target, 'level', None):
                self.draw_string("level %d" % self.examine_target.level, self.examine_display, cur_x, cur_y)
                cur_y += self.linesize

            cur_y += self.linesize

            is_passive = isinstance(self.examine_target, Upgrade) and not self.examine_target.prereq

            if not hasattr(self.examine_target, "no_display_stats"):
                # Autogen boring part of description
                for tag, bonuses in self.examine_target.tag_bonuses.items():
                    for attr, val in bonuses.items():
                        if attr == "requires_los":
                            continue
                        if val >= 0:
                            word = "gain"
                        else:
                            val = -val
                            word = "lose"
                        #cur_color = tag.color
                        if attr in tooltip_colors:
                            fmt = "[%s] spells and skills %s [%s_%s:%s]." % (tag.name, word, val, attr, attr)
                        else:
                            fmt = "[%s] spells and skills %s %s %s." % (tag.name, word, val, format_attr(attr))
                        lines = self.draw_wrapped_string(fmt, self.examine_display, cur_x, cur_y, width=width)
                        cur_y += (lines+1) * self.linesize
                    cur_y += self.linesize

                for spell, bonuses in self.examine_target.spell_bonuses.items():
                    spell_ex = spell()

                    useful_bonuses = [(attr, val) for (attr, val) in bonuses.items() if hasattr(spell_ex, attr) or (not isinstance(val, float) and attr in attr_colors.keys())]
                    if not useful_bonuses:
                        continue

                    for attr, val in useful_bonuses:
                        if attr == "requires_los":
                            continue
                        if val >= 0:
                            word = "gains"
                        else:
                            val = -val
                            word = "loses"
                        upgrade_bonus = not hasattr(spell_ex, attr) and attr in attr_colors.keys()
                        if attr in tooltip_colors:
                            fmt = "%s %s [%s_%s:%s]%s" % (spell_ex.name, word, val, attr, attr, " if its upgrades use this stat" if upgrade_bonus else "")
                        else:
                            fmt = "%s %s %s %s%s" % (spell_ex.name, word, val, format_attr(attr), " if its upgrades use this stat" if upgrade_bonus else "")
                        lines = self.draw_wrapped_string(fmt, self.examine_display, cur_x, cur_y, width=width)
                        cur_y += (lines+1) * self.linesize
                    cur_y += self.linesize

                for attr, val in self.examine_target.global_bonuses.items():
                    if attr == "requires_los":
                        continue
                    if val >= 0:
                        word = "gain"
                    else:
                        val = -val
                        word = "lose"
                    if attr in tooltip_colors:
                        fmt = "All spells and skills %s [%s_%s:%s]" % (word, val, attr, attr)
                    else:
                        fmt = "All spells and skills %s %s %s" % (word, val, format_attr(attr))
                    lines = self.draw_wrapped_string(fmt, self.examine_display, cur_x, cur_y, width)
                    cur_y += (lines+1) * self.linesize

                has_resists = False
                for tag in Tags:
                    if tag not in self.examine_target.resists or tag == Tags.Heal:
                        continue
                    self.draw_string('%d%% Resist %s' % (self.examine_target.resists[tag], tag.name), self.examine_display, cur_x, cur_y, tag.color.to_tup())
                    has_resists = True
                    cur_y += self.linesize

                if has_resists:
                    cur_y += self.linesize

                amount = self.examine_target.resists[Tags.Heal]
                if amount != 0:
                    if amount > 0:
                        word = "Penalty"
                    else:
                        amount *= -1
                        word = "Bonus"
                    self.draw_string('%d%% Healing %s' % (amount, word), self.examine_display, cur_x, cur_y, Tags.Heal.color.to_tup())
                    cur_y += self.linesize*2

            desc = self.examine_target.get_description()
            if not desc:
                desc = self.examine_target.get_tooltip()

            # Warn player about replacing shrine buffs
            if getattr(self.examine_target, 'shrine_name', None):
                existing = [b for b in self.game.p1.buffs if isinstance(b, Upgrade) and b.prereq == self.examine_target.prereq and b.shrine_name and b != self.examine_target] 
                if existing:
                    if not desc:
                        desc = ""
                    desc += "\nWARNING: Will replace %s" % existing[0].name

            if desc:
                self.draw_wrapped_string(desc, self.examine_display, cur_x, cur_y, width, extra_space=True)

    if cls is HeavenlyIdol:

        def cast_instant(self, x, y):

            idol = Unit()
            idol.name = "Idol of Beauty"
            idol.asset_name = "heavenly_idol"

            idol.max_hp = self.get_stat('minion_health')
            idol.shields = self.get_stat('shields')
            idol.stationary = True

            idol.resists[Tags.Physical] = 75
            
            idol.tags = [Tags.Construct, Tags.Holy, Tags.Lightning]

            idol.buffs.append(BeautyIdolBuff(self))
            idol.turns_to_death = self.get_stat('minion_duration')

            if self.get_stat("fire_gaze"):
                gaze = SimpleRangedAttack(damage=self.get_stat("minion_damage", base=8), range=self.get_stat("minion_range", base=10), beam=True, damage_type=Tags.Fire)
                gaze.name = "Fiery Gaze"
                idol.spells.append(gaze)

            self.summon(idol, Point(x, y))

    if cls is Level:

        def set_default_resitances(self, unit):

            if Tags.Metallic in unit.tags:
                unit.resists.setdefault(Tags.Fire, 50)
                unit.resists.setdefault(Tags.Physical, 50)
                unit.resists.setdefault(Tags.Lightning, 100)
                unit.resists.setdefault(Tags.Ice, 100)

            if Tags.Glass in unit.tags:
                unit.resists.setdefault(Tags.Fire, 50)
                unit.resists.setdefault(Tags.Physical, -100)
                unit.resists.setdefault(Tags.Lightning, 100)
                unit.resists.setdefault(Tags.Ice, 100)

            if Tags.Demon in unit.tags:
                unit.resists.setdefault(Tags.Holy, -100)
                unit.resists.setdefault(Tags.Dark, 100)

            # Set undead resistances after metallic, so metallic undead units are immune to ice.
            if Tags.Undead in unit.tags:
                unit.resists.setdefault(Tags.Holy, -100)
                unit.resists.setdefault(Tags.Dark, 100)
                unit.resists.setdefault(Tags.Ice, 50)

            # Poison only works on living, nature, or demons.  Not so hot vs arcane, constructs, ect.
            if Tags.Living in unit.tags:
                unit.resists.setdefault(Tags.Poison, 0)
            if Tags.Nature in unit.tags:
                unit.resists.setdefault(Tags.Poison, 0)
            elif Tags.Demon in unit.tags:
                unit.resists.setdefault(Tags.Poison, 0)
            else:
                unit.resists.setdefault(Tags.Poison, 100)

        def can_move(self, unit, x, y, teleport=False, force_swap=False):

            if not teleport and distance(Point(unit.x, unit.y), Point(x, y), diag=True) > 1.5:
                return False

            if not self.is_point_in_bounds(Point(x, y)):
                return False

            blocker = self.tiles[x][y].unit
            if blocker is not None:
                if force_swap:
                    # Even with force swap, cannot force walkers onto chasms
                    if not blocker.flying and not self.tiles[unit.x][unit.y].can_walk:
                        return False

                elif not unit.is_player_controlled or unit.team != blocker.team:
                    return False

            if not unit.flying:
                if not self.can_walk(x, y):
                    return False
            else:
                if not self.tiles[x][y].can_fly:
                    return False

            return True

    if cls is RadiantCold:

        def get_description(self):
            return "Whenever you cast an [ice] spell, [freeze] the nearest unfrozen enemy to that spell's target for [{duration}_turns:duration].\nEnemies immune to [ice] will be ignored.".format(**self.fmt_dict())

        def on_cast(self, evt):

            if Tags.Ice not in evt.spell.tags:
                return

            self.owner.level.queue_spell(self.do_freeze(evt))

        def do_freeze(self, evt):
            targets = [u for u in self.owner.level.units if are_hostile(self.owner, u) and not u.has_buff(FrozenBuff) and u.resists[Tags.Ice] < 100]
            if targets:
                target = min(targets, key=lambda u: distance(evt, u))
                self.owner.level.show_path_effect(Point(evt.x, evt.y), target, Tags.Ice, minor=True)
                target.apply_buff(FrozenBuff(), self.get_stat('duration'))

            yield

    if cls is FrozenSkullShrineBuff:

        def on_init(self):
            OnKillShrineBuff.on_init(self)
            self.duration = 2
            self.num_targets = 4

        def on_kill(self, unit):
            targets = self.owner.level.get_units_in_los(unit)
            targets = [t for t in targets if are_hostile(self.owner, t) and t.resists[Tags.Ice] < 100]
            if not targets:
                return
            random.shuffle(targets)
            duration = self.get_stat("duration")
            for u in targets[:self.get_stat("num_targets")]:
                u.apply_buff(FrozenBuff(), duration)

        def get_description(self):
            return ("On kill, [freeze] up to [{num_targets}:num_targets] enemies in line of sight of the slain unit for [{duration}_turns:duration].\nEnemies immune to [ice] will be ignored.").format(**self.fmt_dict())

    if cls is SteamAnima:

        def on_unfrozen(self, evt):
            if evt.dtype != Tags.Fire:
                return

            for _ in range(self.get_stat('num_summons')):
                elemental = Unit()
                elemental.name = "Steam Elemental"
                elemental.max_hp = self.get_stat('minion_health')
                elemental.resists[Tags.Physical] = 100
                elemental.resists[Tags.Fire] = 100
                elemental.resists[Tags.Ice] = 100
                elemental.tags = [Tags.Elemental, Tags.Fire, Tags.Ice]
                elemental.turns_to_death = self.get_stat('minion_duration')
                elemental.spells.append(SimpleRangedAttack(damage=self.get_stat('minion_damage'), damage_type=Tags.Fire, range=self.get_stat('minion_range')))

                self.summon(elemental, target=evt.unit)

    if cls is SealedFateBuff:

        def on_advance(self):
            if self.turns_left == 1:
                self.owner.deal_damage(self.spell.get_stat('damage'), Tags.Dark, self.spell)

                if self.spell.get_stat('spreads'):
                    possible_targets = [u for u in self.owner.level.get_units_in_los(self.owner) if u is not self.owner and are_hostile(u, self.spell.owner) and not u.has_buff(SealedFateBuff)]
                    if possible_targets:
                        target = random.choice(possible_targets)
                        target.apply_buff(SealedFateBuff(self.spell), self.spell.get_stat('delay'))

    if cls is SummonSpiderQueen:

        def on_init(self):
            self.name = "Spider Queen"
            self.tags = [Tags.Nature, Tags.Conjuration]

            self.max_charges = 2
            self.level = 5

            self.upgrades["aether"] = (1, 3, "Aether Queen", "Summon an aether spider queen instead.", "species")
            self.upgrades["steel"] = (1, 3, "Steel Queen", "Summon a steel spider queen instead.", "species")

            self.must_target_walkable = True
            self.must_target_empty = True

            self.minion_damage = GiantSpider().spells[0].damage
            self.minion_health = 14

            self.num_summons = 4

    if cls is BoonShrineBuff:

        def on_init(self):
            self.ally_map = defaultdict(int)
            self.owner_triggers[EventOnSpellCast] = self.on_spell_cast

        def on_advance(self):
            for unit in list(self.ally_map.keys()):
                if unit.is_alive():
                    self.ally_map[unit] += 1
                else:
                    self.ally_map.pop(unit)

        def on_spell_cast(self, evt):
            if not type(evt.spell) == self.spell_class:
                return

            allies = [u for u in self.owner.level.units if u is not self.owner and not are_hostile(self.owner, u)]
            if not allies:
                return
            
            never_cast = [u for u in allies if u not in self.ally_map]
            if never_cast:
                newcaster = random.choice(never_cast)
            else:
                newcaster = max(allies, key=lambda u: self.ally_map[u])

            spell = type(evt.spell)()
            spell.cur_charges = 1
            spell.caster = newcaster
            spell.owner = newcaster
            spell.statholder = self.owner

            if spell.can_cast(newcaster.x, newcaster.y):
                self.owner.level.act_cast(newcaster, spell, newcaster.x, newcaster.y)

    if cls is BoonShrine:

        def on_init(self):
            self.name = "Boon"
            self.tags = [Tags.Enchantment]
            self.description = "Self targeted spells only.\nWhenever you cast this spell, an ally also casts it.\nAllies who have never cast this spell are prioritized, then allies who have cast this spell the longest time ago are prioritized."
            self.buff_class = BoonShrineBuff

    if cls is SpiderWeb:

        def __init__(self):
            Cloud.__init__(self)
            self.name = "Spider Web"
            self.color = Color(210, 210, 210)
            self.description = "Any non-spider unit entering the web is stunned for 1 turn.  This destroys the web."
            self.duration = 12

            self.asset_name = 'web'

        def on_damage(self, dtype):
            pass

    if cls is Thorns:

        def get_tooltip(self):
            return "Deals %d %s damage to hostile melee attackers" % (self.damage, self.dtype.name)

    if cls is ToadHop:

        def on_init(self):
            self.name = "Frog Hop"
            self.range = 4
            self.cool_down = 4
            self.description = "Hop closer to the closest reachable enemy if no other ability can be used."
        
        def get_ai_target(self):
            
            for s in self.caster.spells:
                if s is self:
                    continue
                if not s.can_pay_costs():
                    continue
                if s.get_ai_target():
                    return None
            
            targets = [u for u in self.caster.level.units if are_hostile(u, self.caster) and self.caster.can_harm(u)]
            if not targets:
                return None
            paths = {}
            for target in targets:
                path = self.caster.level.find_path(self.caster, target, self.caster, pythonize=True)
                if not path:
                    continue
                paths[target] = path
            if not paths:
                return None
            target = min(paths.keys(), key=lambda t: len(paths[t]))

            for p in reversed(paths[target]):
                if self.caster.level.can_move(self.caster, p.x, p.y, teleport=True) and self.can_cast(p.x, p.y):
                    return p
            return None

        def cast(self, x, y):
            if not self.caster.level.can_move(self.caster, x, y, teleport=True):
                return
            self.caster.invisible = True
            old_point = Point(self.caster.x, self.caster.y)
            self.caster.level.act_move(self.caster, x, y, teleport=True)
            for p in Bolt(self.caster.level, old_point, Point(x, y)):
                self.caster.level.leap_effect(p.x, p.y, Tags.Physical.color, self.caster)
                yield
            self.caster.invisible = False

    if cls is DeathBolt:

        def try_raise(self, caster, unit):
            if unit and not unit.is_alive():
                if self.get_stat('soulbattery'):
                    self.damage += 1
                skeleton = mods.Bugfixes.Bugfixes.raise_skeleton(caster, unit, source=self, summon=False)
                if not skeleton:
                    return
                skeleton.spells[0].damage = self.get_stat('minion_damage')
                self.summon(skeleton, target=unit)
                yield

    if cls is ArchonLightning:

        def get_ai_target(self):
            target = Spell.get_ai_target(self)
            if target:
                return target
            units = [u for u in self.caster.level.get_units_in_ball(self.caster, self.get_stat("range")) if u.shields < 20 and not are_hostile(self.caster, u) and self.can_cast(u.x, u.y)]
            if units:
                unit = random.choice(units)
                return Point(unit.x, unit.y)
            return None

    if cls is CollectedAgony:

        def get_description(self):
            return ("Each turn, deal twice the total of all [poison] damage dealt to all units this turn to the nearest enemy as [dark] damage. Enemies immune to [dark] damage will not be targeted.").format(**self.fmt_dict())

        def on_advance(self):
            if self.charges > 0:
                options = [u for u in self.owner.level.units if are_hostile(u, self.owner) and not is_immune(u, self, Tags.Dark, [])]
                if not options:
                    return
                target = min(options, key=lambda unit: distance(unit, self.owner))
                self.owner.level.queue_spell(self.do_damage(target, 2*self.charges))
            self.charges = 0

    if cls is Horror:

        def on_death(self, evt):
            if not evt.damage_event or evt.damage_event.damage_type != Tags.Dark or not are_hostile(evt.unit, self.owner):
                return
            def eligible(u):
                if u is evt.unit:
                    return False
                if not are_hostile(u, self.owner):
                    return False
                if not self.owner.level.can_see(evt.unit.x, evt.unit.y, u.x, u.y):
                    return False
                return True
            candidates = [u for u in self.owner.level.units if eligible(u)]
            def has_actual_stun(u):
                for buff in u.buffs:
                    if type(buff) == Stun:
                        return True
                return False
            stunned = [u for u in candidates if has_actual_stun(u)]
            random.shuffle(stunned)
            targets = [u for u in candidates if u not in stunned]
            random.shuffle(targets)
            targets.extend(stunned)
            if not targets:
                return
            duration = self.get_stat('duration')
            for c in targets[:self.get_stat("num_targets")]:
                c.apply_buff(Stun(), duration)

    if cls is ShockAndAwe:

        def on_death(self, evt):
            if not evt.damage_event or evt.damage_event.damage_type != Tags.Lightning or not are_hostile(evt.unit, self.owner):
                return
            def eligible(u):
                if u is evt.unit:
                    return False
                if not are_hostile(u, self.owner):
                    return False
                if not self.owner.level.can_see(evt.unit.x, evt.unit.y, u.x, u.y):
                    return False
                return True
            candidates = [u for u in self.owner.level.units if eligible(u)]
            if not candidates:
                return
            not_berserked = [u for u in candidates if not u.has_buff(BerserkBuff)]
            if not_berserked:
                target = random.choice(not_berserked)
            else:
                target = random.choice(candidates)
            target.apply_buff(BerserkBuff(), self.get_stat("duration"))

    for func_name, func in [(key, value) for key, value in locals().items() if callable(value)]:
        if hasattr(cls, func_name):
            setattr(cls, func_name, func)

for cls in [SlimeBuff, HallowFlesh, MeltSpell, MeltBuff, Buff, RedStarShrineBuff, Spell, Unit, ElementalClawBuff, LightningSpireArc, Houndlord, SummonArchon, SummonSeraphim, SummonFloatingEye, InvokeSavagerySpell, ShrapnelBlast, Purestrike, GlassPetrifyBuff, SummonKnights, VoidBeamSpell, DamageAuraBuff, VolcanoTurtleBuff, MordredCorruption, Shrine, PyGameView, HeavenlyIdol, Level, RadiantCold, FrozenSkullShrineBuff, SteamAnima, SealedFateBuff, SummonSpiderQueen, BoonShrineBuff, BoonShrine, SpiderWeb, Thorns, ToadHop, DeathBolt, ArchonLightning, CollectedAgony, Horror, ShockAndAwe]:
    curr_module.modify_class(cls)