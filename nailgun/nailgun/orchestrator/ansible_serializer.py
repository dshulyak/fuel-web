

import os

import yaml

from nailgun.orchestrator import deployment_graph
from nailgun.settings import settings
from nailgun import objects

def puppet(task):
    return {
        'shell':
        'puppet apply {0}'.format(task['parameters']['puppet_manifest'])}


def shell(task):
    return {'shell': task['parameters']['cmd']}


def sync(task):
    return {'shell': 'rsync -c -r --delete {0} {1}'.format(
        task['parameters']['src'], task['parameters']['dst'])}


def copy_data(task):
    return {'copy': 'content={0} dst={1} mode=0644'.format(
        task['parameters']['data'], task['parameters']['dst'])}


def copy_files(task):
    return {'copy': 'dest={{item.dst}} src={{item.dst}} mode=0644',
            'with_items': task['parameters']['files']}


def pre_serialize(task, cluster):
    if task['id'] == 'upload_core_repos':
        task['parameters']['data'] = "deb http://10.109.10.2:8080/2014.2-6.1/ubuntu/x86_64 trusty main"
    elif 'parameters' in task:
        context = {MASTER_IP=settings.MASTER_IP,
                   OPENSTACK_VERSION=cluster.release.version,
                   CLUSTER_ID=cluster.uid}
        params = yaml.dump(task['parameters'])
        task['parameters'] = yaml.load(params.format(**context))


def serialize(task):
    if task['type'] == 'puppet':
        return puppet(task)
    elif task['type'] == 'shell':
        return shell(task)
    elif task['type'] == 'sync':
        return sync(task)
    elif task['type'] == 'copy_files':
        return copy_files(task)
    elif task['type'] == 'upload_file':
        return upload_file(task)


class AnsibleSerializer(object):

    def __init__(self, cluster):
        self.cluster = cluster
        tasks = objects.Cluster.get_deployment_tasks(cluster)
        self.graph = deployment_graph.DeploymentGrap(tasks=tasks)

    def build(self):
        for task in self.graph.find_subgraph(end='deploy_start').topology:
            yield self.build_playbook(
                task['id']+'_playbook', [task], task['role'])

        for group in self.graph.get_groups_subgraph().topology:
            group_tasks = self.graph.get_tasks(group['id']).topology
            yield self.build_playbook(
                group['id'], group_tasks, group['role'])

        for task in self.graph.find_subgraph(start='deploy_end').topology:
            yield self.build_playbook(
                task['id']+'_playbook', [task], task['role'])

    def build_playbook(self, name, tasks, roles):
        if roles == '*':
            hosts = 'all'
        elif roles == 'master':
            hosts = 'localhost'
        else:
            hosts = roles
        serialized = []
        for t in tasks:
            pre_serialize(t, self.cluster):
            stask = serialize(t)
            if stask:
                serialized.append(stask)
        return {
            'hosts': hosts,
            'name': name,
            'tasks': serialized
            }


def create_playbook(cluster):
    ansible = AnsibleSerializer(cluster)
    cwd = '/var/www/nailgun/cluster{0}/'.format(cluster.uid)
    main = []
    for playbook in ansible.build():
        full_path = os.path.join(cwd, playbook['name'] + '.yml')
        with open(full_path, 'w') as f:
            f.write(yaml.safe_dump(playbook, default_flow_style=False))
        main.append({'include': full_path})

    main_full_path = os.path.join(cwd, 'main.yml')
    with open(main_full_path, 'w') as f:
        f.write(yaml.safe_dump(main, default_flow_style=False))

def main():
    cluster = objects.Cluster.get_by_uid(sys.argv[1])
    create_playbook(cluster)
