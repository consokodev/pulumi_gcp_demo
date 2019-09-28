import json
from pprint import pprint

import yaml
from pulumi import Output, ResourceOptions, export
from pulumi_gcp import Provider, compute, storage

# provider = Provider()

def load_config(config_file):
    r"""
        Load yaml config file
    """
    with open(config_file, 'r') as stream:
        try:
            return dict(yaml.safe_load(stream))
        except yaml.YAMLError as exc:
            print(exc)

def create_vpc(config_file):
    r"""
        Generate network block

        Dict load from config file
        {
        "vpctest": {
            "auto_create_subnetworks": false,
            "region": {
                "asia-southeast1": {
                    "subnet": [
                        "10.26.1.0/24"
                    ],
                    "subnet_name": "webzone"
                },
                "us-central1": {
                    "subnet": [
                        "10.26.1.0/24"
                    ],
                    "subnet_name": "dbzone"
                }
            },
            "routing_mode": "GLOBAL",
            "vpc_name": "vpctest"
        },
    }
    """ 

    config_vpcs = load_config(config_file) ###Load VPC config

    all_created_vpcs, all_created_subnetwork = [], []

    ####Generate VPC from yaml config files = dict
    for key, value in config_vpcs.items():
        network_instance = compute.Network(
            value["vpc_name"],
            name=value["vpc_name"],  ####Disable auto-naming
            auto_create_subnetworks = value["auto_create_subnetworks"],
            routing_mode = value["routing_mode"]
        )
        all_created_vpcs.append(network_instance)

        all_subnet_per_vpc = []
        ######Generate subnet for vpc if auto_create_subnetworks == false
        if(value["auto_create_subnetworks"] == False):
            for region, region_val in value["region"].items():
                for item in region_val["subnet"]:
                    subnetwork_instance = compute.Subnetwork(
                        region_val["subnet_name"],
                        name=region_val["subnet_name"], ####Disable auto-naming
                        ip_cidr_range = item,
                        network = network_instance.self_link,
                        region = region,
                        opts = ResourceOptions(depends_on=[network_instance])
                    )
                    all_subnet_per_vpc.append(item)
                    all_created_subnetwork.append(subnetwork_instance)
                
        #######Generate internal FW block
        rule_name = "allowinternal" + value["vpc_name"]
        rule_name = compute.Firewall(
            rule_name,
            network = network_instance,
            allows = [
                {
                    "protocol": "icmp",
                },
                {
                    "protocol": "tcp",
                    "ports": ["0-65535"]
                },
                {
                    "protocol": "udp",
                    "ports": ["0-65535"]
                }
            ],
            source_ranges = all_subnet_per_vpc
        )

        #########Generate FW outside FW block
        rule_name = "allowingress" + value["vpc_name"]
        rule_name = compute.Firewall(
            rule_name,
            network = network_instance,
            allows = [
                {
                    "protocol": "tcp",
                    "ports": ["22", "80", "443"]
                }
            ]
        )
        
    return {
        "all_created_vpcs": all_created_vpcs, 
        "all_created_subnetwork": all_created_subnetwork
    }


def create_instances(config_file, vpc_result):
    r"""
        Generate instances block

        Dict load from config file
        {
            'instance_db': {'boot_disk': {'image': 'centos-cloud/centos-7-v20190116'},
                'count': 1,
                'instance_names': ['servertest3'],
                'machine_type': 'f1-micro',
                'metadata': {'phucdh': 'ssh-rsa '
                                    'AAAAB3NzaC1yc2EAAAADAQABAAACAQC+K8iUKOFqb1+RTpnrjLZ4BYcbucqOW488EljBXErj5IJJma1Zr8gxBuB5BcJlbEc2JMtHRdpW7g9bpngMBnD8d0nYbWmdLwEjSdPiSM1bKhBbgxk1eIu8/rQWs1mesXNTku8BJggolVUsYf5Hh6pkQoUV7A54pIytAXRJ2QhXqoXnvxvESxG+x8KH2KgIa2yypI+sfilBhjSFtwNMMC5IsLcWq4clVFKdm0Rv63h+CwAyNjP52fBoBuOdJRSfyIjYOu6a7piJcopa4Zu8vwNjRAYzTvzazRFyRa9p0wYX/ogJahUGoSBEAaGKLgPCI1GdtOc+r00u2u8Ie2SKw1zaj97DM7bv/lAIcLnF3VPiBH65UtampC+EdOS2lHuOsfwdsyNssCABlp3xvVrqiBIE2TJnYTqLRQMy4QAbOqXRMeKwodyGVWyXebrCcdCMxQ69jSYAcecHRK6rMzHuxHH9taOl0MJS63d3MLmcj0XblxpJdhG5XOKnkQSDezbhgAR6rkp9caO5YGLOGIfdeW52ClwHD/ftdeElJWi8TAK+z2hyxkDeI9M88MPDVHhWAkf840mao3MC2JMS3E7tTfrwHZlGNm22HTDvT/2dxGoudiDHCYdPBvM8eBiXJ3yuzetuflBD1yynCQ5LpqEwy3Zoz+yeo5gbWkJY2/MjGAai0w== '
                                    'dinhhuuphuc.it@gmail.com'},
                'network_interfaces': {'network': 'vpctest',
                                    'subnet_name': 'dbzone'},
                'script': '#!/bin/bash\n'
                        'sudo touch /tmp/a.txt\n'
                        'sudo yum install -y nginx\n'
                        'sudo service nginx start',
                'zone': 'us-central1-a'
        }
    """

    config_instances = load_config(config_file) ###Load instance config file
    json.dumps(str(config_instances), indent=4, sort_keys=True)

    all_created_compute = []
    ######Genereate instances from config file
    for key, value in config_instances.items():
        assert (len(value["instance_names"]) == int(value["count"])), "The number of {instances} (count) and the len of instance_name are not equal"
        if (len(value["instance_names"]) == int(value["count"])):
            for instance in value["instance_names"]:
                instance = compute.Instance(
                    instance,
                    zone = value["zone"], 
                    name = instance,
                    machine_type = value["machine_type"],
                    boot_disk={
                        "initializeParams": {
                            "image": value["boot_disk"]["image"]
                        }
                    },
                    ####Add more network interface to list of a compute need more
                    ####Need to update logic if want to add more interface to compute
                    network_interfaces=[
                        {
                            "network": value["network_interfaces"]["network"],
                            "subnetwork": value["network_interfaces"]["subnet_name"],
                            "accessConfigs": [{

                            }]
                        }
                    ],
                    metadata_startup_script = value["script"],
                    opts = ResourceOptions(depends_on=vpc_result["all_created_subnetwork"]) ####Depends on subnetwork
                    # metadata = {
                    #     value["metadata"]
                    # }
                )
                all_created_compute.append(instance)

    return all_created_compute

# key = compute.ProjectMetadata(
#     "key",
#     metadata = {
#         "phucdh": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC+K8iUKOFqb1+RTpnrjLZ4BYcbucqOW488EljBXErj5IJJma1Zr8gxBuB5BcJlbEc2JMtHRdpW7g9bpngMBnD8d0nYbWmdLwEjSdPiSM1bKhBbgxk1eIu8/rQWs1mesXNTku8BJggolVUsYf5Hh6pkQoUV7A54pIytAXRJ2QhXqoXnvxvESxG+x8KH2KgIa2yypI+sfilBhjSFtwNMMC5IsLcWq4clVFKdm0Rv63h+CwAyNjP52fBoBuOdJRSfyIjYOu6a7piJcopa4Zu8vwNjRAYzTvzazRFyRa9p0wYX/ogJahUGoSBEAaGKLgPCI1GdtOc+r00u2u8Ie2SKw1zaj97DM7bv/lAIcLnF3VPiBH65UtampC+EdOS2lHuOsfwdsyNssCABlp3xvVrqiBIE2TJnYTqLRQMy4QAbOqXRMeKwodyGVWyXebrCcdCMxQ69jSYAcecHRK6rMzHuxHH9taOl0MJS63d3MLmcj0XblxpJdhG5XOKnkQSDezbhgAR6rkp9caO5YGLOGIfdeW52ClwHD/ftdeElJWi8TAK+z2hyxkDeI9M88MPDVHhWAkf840mao3MC2JMS3E7tTfrwHZlGNm22HTDvT/2dxGoudiDHCYdPBvM8eBiXJ3yuzetuflBD1yynCQ5LpqEwy3Zoz+yeo5gbWkJY2/MjGAai0w== dinhhuuphuc.it@gmail.com"
#     }
# )


if(__name__ == "__main__"):

    vpc_result = create_vpc("config_vpcs.yaml")
    compute_result = create_instances("config_instances.yaml", vpc_result)

    ###Export all created objects
    for key, value in vpc_result.items():
        export(key, value)

    export("Compute", compute_result)