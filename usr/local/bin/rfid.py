#!/usr/bin/python3

import logging
import signal

from queue import Queue
from sqlite3 import connect
from threading import Thread
from time import time, sleep

from pyImpinj import ImpinjR2KReader
from pyImpinj.enums import ImpinjR2KFastSwitchInventory

def reader():
	# Setup connection to tag reader
	R2000 = ImpinjR2KReader(tags, address = READER_ADDRESS)
	R2000.connect(SERIAL_PORT)
	R2000.worker_start()
	R2000.temperature()

	# Detect antenna ports to use
	antenna_switching_params = { 'Interval': ANTENNA_REST_PERIOD, 'Repeat': INVENTORY_REPEAT }
	for i in range(0, MAX_ANTENNAS):
		R2000.set_work_antenna(i)
		antenna_switching_params[chr(i + 65)] = i if(R2000.get_rf_port_return_loss(MEASURE_RETURN_LOSS_FREQUENCY) > ANTENNA_CONNECTED_MIN_RETURN_LOSS) else ImpinjR2KFastSwitchInventory.DISABLED

	logging.info (antenna_switching_params)

	# Set output power
	R2000.fast_power (POWER_OUTPUT)

	# Read tags
	while readTags:
		R2000.fast_switch_ant_inventory(antenna_switching_params)
		sleep (COOLDOWN_PERIOD)

def tracker():
	con = connect(DATABASE, isolation_level=None)
	con.execute('pragma journal_mode=wal')
	con.execute('''CREATE TABLE IF NOT EXISTS "tagreads" ("timestamp" INTEGER DEFAULT (CAST(strftime('%s', 'now') AS INT)), "epc" BLOB, "antenna" INTEGER, "frequency" REAL, "rssi" INTEGER, UNIQUE("epc", "antenna"))''')
	con.execute('''CREATE INDEX IF NOT EXISTS "epcindex" ON "tagreads"("epc", "timestamp")''')

	while True:
		# Get data from tag reader
		item = tags.get()

		# Shutting down
		if item is None:
			break

		# Handle case of data representing a tag
		if item['type'] == 'TAG':
			con.execute('''INSERT OR IGNORE INTO "tagreads" ("epc", "antenna", "frequency", "rssi") VALUES (?, ?, ?, ?)''', (item['epc'], item['antenna'], item['frequency'], item['rssi']))

		# Handle case of an error
		elif item['type'] == 'ERROR':
			logging.warning(item)

		# Handle anything else
		else:
			logging.info (item)

if __name__ == "__main__":
	SERIAL_PORT = '/dev/rfid'
	READER_ADDRESS = 1
	MAX_ANTENNAS = 4
	POWER_OUTPUT = 33	# 22-33 dBm
	ANTENNA_CONNECTED_MIN_RETURN_LOSS = 3
	MEASURE_RETURN_LOSS_FREQUENCY = 902
	ANTENNA_REST_PERIOD = 255
	INVENTORY_REPEAT = 100
	COOLDOWN_PERIOD = 0.2	# Seconds to sleep between inventory scans

	DATABASE = '/var/local/tags.sqlite3'

	#logging.basicConfig (filename = '/tmp/rfid.log', level = logging.DEBUG)
	logging.basicConfig (level = logging.INFO)

	tags = Queue()
	readTags = True
	running = True

	threadReader = Thread(target = reader, daemon = True)
	threadTracker = Thread(target = tracker, daemon = True)

	threadReader.start()
	threadTracker.start()

	signal.sigwait([signal.SIGINT, signal.SIGTERM])

	readTags = False
	threadReader.join()
	tags.put(None)
	threadTracker.join()
