import json

def get_hits_stats(jsonl_path='hits.jsonl'):
    """
    Reads hits.jsonl, collects stats including the ordered set of norm times and rule_id distribution.
    Returns a dict with total hits, ordered norm times, and rule_id distribution.
    """
    norm_times = set()
    total_hits = 0
    rule_id_counts = {}

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            if 'norm_time' in data:
                norm_times.add(data['norm_time'])
            if 'rule_id' in data:
                rule_id = data['rule_id']
                rule_id_counts[rule_id] = rule_id_counts.get(rule_id, 0) + 1
            total_hits += 1

    ordered_norm_times = sorted(norm_times)
    rule_id_distribution = dict(sorted(rule_id_counts.items()))
    return {
        'total_hits': total_hits,
        'ordered_norm_times': ordered_norm_times,
        'rule_id_distribution': rule_id_distribution
    }


if __name__ == '__main__':
    stats = get_hits_stats()
    for stat in stats:
        print(stat, stats[stat])