"""Byte-bounded, lossless pagination of permitted visible observations."""
import json

def content(ident,observation):
    return [{'type':'inputText','text':json.dumps({'id':ident,'untrusted_visible_data':observation})}]

def pages(snapshot,limit):
    # Units preserve every control and accessibility character; no silent truncation.
    units=[('accessibility',snapshot['accessibility'][i:i+256]) for i in range(0,len(snapshot['accessibility']),256)]
    units += [('controls',row) for row in snapshot['controls']]
    result=[]; current={'accessibility':'','controls':[]}
    # Reserve space for pagination/snapshot metadata and the response envelope.
    capacity=limit-1000
    if capacity<300: raise ValueError('Visible output limit too small for pagination')
    for kind,value in units:
        candidate={'accessibility':current['accessibility'],'controls':list(current['controls'])}
        if kind=='controls': candidate[kind].append(value)
        else: candidate[kind]+=value
        if len(json.dumps(content('observation-999',candidate)).encode())>capacity:
            if not current['accessibility'] and not current['controls']: raise ValueError('Individual visible item too large')
            result.append(current); current={'accessibility':'','controls':[]}
            if kind=='controls': current[kind]=[value]
            else: current[kind]=value
            if len(json.dumps(content('observation-999',current)).encode())>capacity: raise ValueError('Individual visible item too large')
        else: current=candidate
    result.append(current)
    if len(result)>100: raise ValueError('Visible snapshot pagination limit')
    return result
