import json, yaml

class Abc():
    pass

with open("config_vpcs.yaml", 'r') as stream:
    try:
        config_vpcs = dict(yaml.safe_load(stream))
    except yaml.YAMLError as exc:
        print(exc)

for key, value in config_vpcs.items():
    value["vpc_name"] = Abc()
    print(value["vpc_name"])


