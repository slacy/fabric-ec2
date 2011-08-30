import re
import time

from fabric.api import *

import ec2


env.user = 'ubuntu'
env.key_filename = '/home/slacy/.ssh/slacykey.pem'

def init_roles():
    ec2_machines = ec2.get_all_machines()

    for mach in ec2_machines:
        roles = re.split('[, ]+', mach.tags['role'])
        for r in roles:
            if r not in env.roledefs:
                env.roledefs[r] = []
            if mach.public_dns_name:
                env.roledefs[r].append(mach.public_dns_name)

        ec2_dns = [mach.public_dns_name for mach in ec2_machines]
    # print "roledefs: %s" % env.roledefs

@roles('source')
def git_push():
    with cd('/home/ubuntu'):
        run('if [ ! -d ~/pvn2.git ]; then '
            'git init --bare ./pvn2.git; '
            'git clone ./pvn2.git ./pvn2; '
            'fi')
    local('git push ssh://%s@%s/home/ubuntu/pvn2.git master' % (
            env.user, env.host_string))
    local_pull()


@roles('source')
def git_pull():
    # local('git push ssh://%s/home/ubuntu/pvn2.git master' % env.host_string)
    local('git pull ssh://%s@%s/home/ubuntu/pvn2.git master' % (
            env.user, env.host_string))


def local_pull():
    with cd('/home/ubuntu/pvn2'):
        run('git pull')


@roles('source')
def virtualenv_setup():
    local_pull()
    with cd('/home/ubuntu/pvn2'):
        run('source ./pipdata/setup')
    # with cd('/home/ubuntu/pvn2'):
    #     run('source ./activate; pushd minimongo; python ./setup.py develop; popd')
    # with cd('/home/ubuntu/pvn2'):
    #     run('source ./activate; pushd methodpickle; python ./setup.py develop; popd')
    # with cd('/home/ubuntu/pvn2'):
    #     run('source ./activate; pushd mvp; python ./setup.py develop; popd')


@roles('mongodb')
def bringup_raid():
    sudo('mdadm /dev/md0 --assemble /dev/sdf /dev/sdg /dev/sdh /dev/sdi')
    # run('pvcreate /dev/md0')
    # run('vgcreate vgm0 /dev/md0')
    # run('lvcreate --name lvm0 --size 499G vgm0')
    # run('mkdir /data')
    sudo('mount /dev/vgm0/lvm0 /data')

@roles('ubuntu')
def dist_upgrade():
    sudo('apt-get -qy update')
    sudo('apt-get -qy dist-upgrade')

@roles('ubuntu')
def screenrc():
    put('./doc/.screenrc', '/home/ubuntu/.screenrc')

@roles('mongodb')
def backup_db():
    backup_name = time.strftime('%y%m%d_%H%M')
    tmpdir = run('mktemp -d --tmpdir=/data/tmp').strip()
    fmt = {'backup': backup_name,
           'tmpdir': tmpdir,
           'tarfile': '%s/%s.tar.bz' % (tmpdir, backup_name)}
    with cd(tmpdir):
        run('mongodump -d pvn2 -o %s' % backup_name)
        run('mongodump -d web -o %s' % backup_name)
        run('mongodump -d task -o %s' % backup_name)
        run('tar cvf %(tarfile)s --use-compress-prog=pbzip2 %(backup)s' % fmt)
#    get("%(tmpdir)s/%(backup)s.tar.bz2" % {'tmpdir': tmpdir, 'backup': backup_name},
#        "/tmp/%(backup)s.tar.bz2" % {'backup': backup_name})
    run('/home/ubuntu/pvn2/env/bin/s3put '
        '-a "<YOUR KEY HERE>" '
        '-s "<YOUR SECRET KEY HERE>" '
        '-b pvn2backup -p %(tmpdir)s -g private '
        '%(tarfile)s' % fmt)
    run('rm -r %s' % tmpdir)

init_roles()
