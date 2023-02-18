PLEASE CHECK THE DISCORD THREAD FOR UPDATE NOTICES, AND RE-DOWNLOAD THE MOD WHENEVER THERE'S AN UPDATE.

This mod requires my Bugfixes mod, which can be found here: https://github.com/jh1993/Bugfixes

To install this mod, click on the green "Code" button on this page, then "Download ZIP". Please rename the "NoMoreScams-main" folder to "NoMoreScams" before putting it into your mods folder.

This mod changes a number of things so that they behave exactly as described, when it can be argued that either the behavior or the description should be changed. The "scam" in the name is tongue in cheek and describes the feeling of being cheated when you find that something does not work as advertised, even though it's highly likely that it's simply a mistake rather than intentional.

- Shrine-based redeals no longer affect allies.
- Purestrike no longer damages allies or counts damage after resistances rather than before.
- Melt is now permanent instead of lasting 2 turns.
- Hollow Flesh is no longer limited to living targets.
- If a slime would gain less than 1 max HP, it now has a chance to gain 1 max HP instead of rounding to the next lower integer. This means Arch Conjurer no longer makes slimes take longer to split, on average.
- Minions now take all redeal skills and shrines into account when targeting enemies with immunities. Conditional redeals like Purestrike and Red Star shrine are included.
- Mordred's planeshift will no longer delete minions summoned by conjuration skills, e.g. Faestone.
- If adjacent squares are blocked by minions summoned by conjuration skills, Houndlord will shunt the hellhounds elsewhere. This should definitively fix the Bone Guard + Houndlord scam.
- Searing Seal now actually deals 1 damage per 4 charges instead of per 5 charges.
- Minions will now use spells inherited from the player indiscriminately against all targets regardless of immunity, to make redeals easier. This used to be highly inconsistent as some spells arbitrarily had damage_type defined and some didn't.
- Metallic undead units are now ice-immune like all other metallic units. The only reason they weren't ice-immune in the first place was because the default 50% ice resistance of undead units happened to be set before the default ice immunity of metallic units.
- Archon, Seraph, and Idol of Beauty units now have their proper elemental tags.
- Upon reincarnation, Floating Eye now casts your eye spells again.
- Invoke Savagery will no longer try to hit physical-immune enemies unless the minion doing the attack has physical redeals.
- Mordred's planeshift and Orb of Corruption now have the same sanity checks that ensure all floor tiles are reachable from other floor tiles, and all chasm tiles are reachable from other chasm tiles by flying units. In other words, no more softlocks.
- The initial blast of Shrapnel Blast now actually deals damage to all points adjacent to the wall, not just a 1-radius burst.
- Lightning Spire will now target lightning-immune enemies if you have the resistance debuff upgrade, even if you don't have Holy Thunder.
- Units will now treat soul-jarred enemies with 1 HP as invalid targets for offensive spells.
- Glass enemies are no longer secretly immune to glassify.
- Knightly Oath now has a minion range stat of 6 for the purpose of shrine bonuses, and will now try to summon champions before regular knights if there isn't enough room to summon all the knights.
- Void Beam no longer destroys clouds.
- Void Phoenix and volcano turtles can no longer destroy walls, preventing softlocks that can happen when enemies are summoned inside unreachable pockets surrounded by walls.
- If a spell does not innately have a stat, it can now still benefit from shrines that give flat bonuses to that stat, in case the spell makes use of that stat through an upgrade; the tooltip is changed to say so accordingly. However, that spell won't be able to benefit from percentage bonuses to that stat, since any percentage of 0 is still 0.
- The player can now swap places with stationary allies, preventing some softlocks.
- Radiant Chill and Frozen Skull shrine will now ignore ice-immune enemies when choosing their targets, resulting in no dud freezing attempts.
- Steam elementals from Steam Anima are now also ice units.
- Seal Fate Spreading Curse no longer tries to apply the debuff to targets already affected by the debuff.
- Metallic undead units are now ice-immune like all other metallic units. The only reason they weren't ice-immune in the first place was because the default 50% ice resistance of undead units happened to be set before the default ice immunity of metallic units.
- Spider Queen now has a minion health stat of 14 rather than 10, for the purpose of Vigor shrine.