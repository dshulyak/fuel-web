

import os

import yaml

from nailgun.orchestrator import deployment_graph
from nailgun.settings import settings
from nailgun import objects


CWD = '/var/www/nailgun/deployments/'


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
        context = {'MASTER_IP': settings.MASTER_IP,
                   'OPENSTACK_VERSION': cluster.release.version,
                   'CLUSTER_ID': cluster.uid}
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


def async_status(name):
    return {
        'async_status': 'jid={{ {name}.ansible_job_id }}'.format(name=name),
        'register': 'job',
        'until': 'job.finished',
        'retries': '1600'}


def async_play(name, full_path, requires):
    if requires:
        for require in requires:
            yield async_status(require)

    yield  {'shell': 'ansible-playbook {0}'.format(full_path),
            'register': name,
            'async': 3600,
            'poll': 0}



def playbook(name, tasks, roles):

    if roles == '*':
        hosts = 'all'
    elif roles == 'master':
        hosts = 'localhost'
    else:
        hosts = roles

    serialized = []
    for t in tasks:
        # pre_serialize(t, self.cluster)
        stask = serialize(t)
        if stask:
            serialized.append(stask)

    return {
        'hosts': hosts,
        'name': name,
        'tasks': serialized
        }


def write_data(name, data):
    full_path = os.path.join(CWD, name + '.yml')
    with open(full_path, 'w') as f:
        f.write(yaml.safe_dump(data, default_flow_style=False))


def create_playbook(name, tasks, hosts):
    play = playbook(name, tasks, hosts)

    write_data(name, [play])
    return os.path.join(CWD, name + '.yml')


def prepare(cluster):

    graph = deployment_graph.DeploymentGraph(
        tasks=objects.Cluster.get_deployment_tasks(cluster))
    main_tasks = []
    for group in self.graph.get_groups_subgraph().topology:
        group_tasks = self.graph.get_tasks(group['id']).topology
        path = create_playbook(group['id'], group_tasks, group['role'])

        main_tasks.append([{'include': path}])

    write_data('groups', main_tasks)


def main():
    cluster = objects.Cluster.get_by_uid(sys.argv[1])
    prepare(cluster)
