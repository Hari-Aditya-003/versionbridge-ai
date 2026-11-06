"""Category metrics from explicit evaluated records; missing checks are not passes."""
from collections import defaultdict


def summarize(records):
    groups=defaultdict(list)
    for r in records:
        groups[(r['category'],r['model'])].append(r)
    output=[]
    for (category,model),rows in sorted(groups.items()):
        verified=sum(r.get('eligible') is True and r.get('independent_pass') is True for r in rows)
        false=sum(r.get('eligible') is True and r.get('independent_pass') is False for r in rows)
        cost=sum(r.get('reserved_usd',0) for r in rows)
        output.append({'category':category,'model':model,'tasks':len(rows),'verified':verified,
                       'verified_repair_rate':verified/len(rows),'false_acceptances':false,
                       'false_acceptance_rate':false/len(rows),'latency_ms':sum(r.get('latency_ms',0) for r in rows),
                       'reserved_usd':cost,'reserved_cost_per_verified_repair':cost/verified if verified else None})
    return {'groups':output,'promotion':'advisory only; paired independent holdouts and backend availability required',
            'billing':'reserved inference cost, not provider invoice'}
