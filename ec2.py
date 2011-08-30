import boto
import re
import socket

AWS_ACCESS_KEY_ID=<YOUR ACCESS KEY HERE>
AWS_SECRET_ACCESS_KEY=<YOUR SECRET ACCESS KEY HERE>


def get_all_machines():
    ec2_conn = boto.connect_ec2(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    reservations = ec2_conn.get_all_instances()
    all_machines = []
    for reservation in reservations:
        all_machines += reservation.instances
    return all_machines


def this_machine():
    all_machines = get_all_machines()
    hostname = socket.gethostname()
    parts = hostname.split('-')
    my_ip_str = '.'.join(parts[1:5])
    for mach in all_machines:
        if mach.private_ip_address == my_ip_str:
            return mach
    # We're not on EC2
    return None

def on_ec2():
    return this_machine() != None

def machine_roles(role):
    machines = get_all_machines()
    matches = []
    for mach in machines:
        roles = re.split('[, ]+', mach.tags['role'])
        if role in roles:
            matches.append(mach)
    return matches
