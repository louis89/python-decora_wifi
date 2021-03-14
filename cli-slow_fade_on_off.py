#!/usr/bin/python3

from decora_wifi import DecoraWiFiSession
from decora_wifi.models.person import Person
from decora_wifi.models.residential_account import ResidentialAccount
from decora_wifi.models.residence import Residence

import sys, sched, time

def find_all_residences(session):
	all_residences = []
	perms = session.user.get_residential_permissions()
	for permission in perms:
	    if permission.residentialAccountId is not None:
	        acct = ResidentialAccount(session, permission.residentialAccountId)
	        for res in acct.get_residences():
	            all_residences.append(res)
	    elif permission.residenceId is not None:
	        res = Residence(session, permission.residenceId)
	        print('Residence: {}'.format(res))
	        all_residences.append(res)
	return all_residences

def find_all_iot_dimmer_switches_by_ids(all_residences, dimmer_switch_ids):
	all_switches = []
	for residence in all_residences:
		for decora_switch_id in dimmer_switch_ids:
			all_switches.append(residence.find_by_id_iot_switches(decora_switch_id))
	return all_switches

def brighten_on(switches, scheduler, tick_delay):
	any_switches_not_full_brightness = False
	for switch in switches: 
		if switch.power == 'OFF':
			switch.update_attributes({'brightness':switch.minLevel, 'power':'ON'})
			print('Brightened {} ON'.format( switch.id ))
			any_switches_not_full_brightness = True
		elif switch.brightness < switch.maxLevel:
			switch.update_attributes({'brightness':switch.brightness + 1})
			print('Brightened {} one tick to {}'.format( switch.id, switch.brightness ))
			any_switches_not_full_brightness = True
	if any_switches_not_full_brightness:
		scheduler.enter(tick_delay, 1, brighten_on, (switches, scheduler, tick_delay))
		scheduler.run()

def fade_off(switches, scheduler, tick_delay):
	any_switches_on = False
	for switch in switches: 
		if switch.brightness > switch.minLevel:
			switch.update_attributes({'brightness':switch.brightness - 1})
			print('Faded {} one tick to {}'.format( switch.id , switch.brightness ))
			any_switches_on = True
		elif switch.power != 'OFF':
			switch.update_attributes({'power':'OFF'})
			print('Faded {} OFF'.format( switch.id ))
	if any_switches_on:
		scheduler.enter(tick_delay, 1, fade_off, (switches, scheduler, tick_delay))
		scheduler.run()

if len(sys.argv) < 6:
    print('Usage: ./cli-slow_fade_on_off.py [email] [password] [ON|OFF] [Fade period in seconds (float)] [dimmer switch IDs (comma separated)]')

email = sys.argv[1]
password = sys.argv[2]
command = sys.argv[3]
fade_period_seconds = float(sys.argv[4])
dimmer_switch_ids = sys.argv[5].split(',')

session = DecoraWiFiSession()
session.login(email, password)

residences = find_all_residences(session)
switches = find_all_iot_dimmer_switches_by_ids(residences, dimmer_switch_ids)

if command == 'ON':
	print('Brighten ON: {}'.format( switches ))
	brighten_on(switches, sched.scheduler(time.time, time.sleep), fade_period_seconds / max(map(lambda switch: switch.maxLevel - (switch.minLevel if switch.power == 'OFF' else switch.brightness), switches)))
elif command == 'OFF':
	print('Fade OFF: {}'.format( switches ))
	fade_off(switches, sched.scheduler(time.time, time.sleep), fade_period_seconds / max(map(lambda switch: switch.brightness - switch.minLevel, switches)))
else:
	raise ValueError('Invalid command ' + command)

