#!/usr/bin/env python3

import subprocess
from pathlib import Path
from pwd import getpwuid
from sys import exit

def retrieve_gpus ():
	gpus = {}
	lines = subprocess.run(
		['/usr/bin/env', 'nvidia-smi', '--format=csv,noheader,nounits', '--query-gpu=index,gpu_uuid,name,memory.used,memory.total,utilization.gpu,persistence_mode'],
		stdout=subprocess.PIPE
	).stdout.decode().strip().split('\n')
	for line in lines:
		values = line.split(', ')
		gpus[values[1]] = {
			'index': int(values[0]),
			'name': values[2],
			'memory_used': int(values[3]),
			'memory_total': int(values[4]),
			'utilization_gpu': int(values[5]),
			'persistence_mode': (values[6] == 'Enabled')
		}
	return gpus

def retrieve_processes ():
	
	processes = []
	
	lines = subprocess.run(
		['/usr/bin/env', 'nvidia-smi', '--format=csv,noheader,nounits', '--query-compute-apps=gpu_uuid,pid,used_memory'],
		stdout=subprocess.PIPE
	).stdout.decode().strip().split('\n')

	if lines[0] == '':
		return []

	for line in lines:
		values = line.split(', ')
		processes.append({
			'gpu_uuid': values[0],
			'pid': int(values[1]),
			'used_gpu_memory': int(values[2]),
		})

	for process in processes:
		p = Path('/proc', str(process['pid']))
		process['user'] = getpwuid(p.stat().st_uid).pw_name
		process['command'] = p.joinpath('cmdline').read_text().replace('\0', ' ')

	return processes

gpus = retrieve_gpus()
processes = retrieve_processes()

if any(map(lambda g: not g['persistence_mode'], gpus.values())):
	print('Consider enabling persistence mode on your GPU(s) for faster response.')
	print('For more information: https://docs.nvidia.com/deploy/driver-persistence/')

print('+----------------------------+------+-------------------+---------+')
print('| GPU                        | %GPU | VRAM              | PROCESS |')
print('|----------------------------+------+-------------------+---------|')

for gpu_uuid, gpu in gpus.items():
	print('| {:3d} {:22} | {:3d}% | {:5d} / {:5d} MiB | {} |'.format(
		gpu['index'],
		'(' + gpu['name'] + ')',
		gpu['utilization_gpu'],
		gpu['memory_used'],
		gpu['memory_total'],
		'Running' if any(map(lambda p: p['gpu_uuid'] == gpu_uuid, processes)) else '-------'
	))

print('|=================================================================|')

if len(processes) == 0:
	print('| No running processes found                                      |')
	print('+-----------------------------------------------------------------+')
	exit()

print('| GPU | USER       | PID     | VRAM      | COMMAND                |')
print('|-----+------------+---------+-----------+------------------------|')

for process in processes:
	print('| {:3d} | {:^10} | {:7d} | {:5d} MiB | {:>22} |'.format(
		gpus[process['gpu_uuid']]['index'],
		process['user'],
		process['pid'],
		process['used_gpu_memory'],
		process['command'][:22]
	))

print('+-----+------------+---------+-----------+------------------------+')