N = 1
with open("/work/YOU-DARE/scrapers/data/United_Kingdom/modernity_individual_links_SPIDER/data_modernity_individual_links_SPIDER.jl") as f:
    for i in range(0, N):
        print(f.readline(), end = '')


def get_keys(dl, keys_list):
    if isinstance(dl, dict):
        keys_list += dl.keys()
        map(lambda x: get_keys(x, keys_list), dl.values())
    elif isinstance(dl, list):
        map(lambda x: get_keys(x, keys_list), dl)

keys = []
get_keys(jdata, keys)

print(keys)

print(list(set(keys)))    # unique list of keys