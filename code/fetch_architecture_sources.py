"""Select official office architecture sources from a remote ZIP by verified HTTP ranges.
No TLS override; no full-archive SHA256 claimed from partial reads.
"""
import argparse
import json
import struct
import subprocess
import zlib
from pathlib import Path,PurePosixPath
from recover_fitting_interfaces import sha

URL='https://www.nordicsustainableconstruction.com/Media/638593249820446520/ARCH.zip'
TOTAL=1579459850
ETAG='"a346724116efda1:0"'


def central_directory(payload):
    entries=[]
    offset=0
    while offset<len(payload):
        if payload[offset:offset+4]!=b'PK\x01\x02':
            raise ValueError('Unsupported central directory signature')
        header=struct.unpack_from('<4s6H3I5H2I',payload,offset)
        _,made,needed,flags,method,time,date,crc,compressed,size,name_len,extra_len,comment_len,disk,internal,external,local=header
        if disk or compressed==0xffffffff or size==0xffffffff or local==0xffffffff:
            raise ValueError('Multi-disk/ZIP64 not supported by bounded downloader')
        name_bytes=payload[offset+46:offset+46+name_len]
        name=name_bytes.decode('utf-8' if flags&0x800 else 'cp437')
        if '\x00' in name or '..' in PurePosixPath(name.replace('\\','/')).parts:
            raise ValueError('Unsafe archive path')
        entries.append({'name':name,'flags':flags,'method':method,'crc32':crc,'compressed_size':compressed,'size':size,'local_offset':local})
        offset+=46+name_len+extra_len+comment_len
    return entries


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--extract-office',action='store_true')
    args=parser.parse_args()
    project=Path(__file__).resolve().parents[1]
    cache=project/'.dsh-state/architecture-cache'
    cache.mkdir(parents=True,exist_ok=True)
    ranges=[]
    def fetch(start,end,label):
        output=cache/(label+'.bin')
        spec={'url':URL,'start':start,'end':end,'total':TOTAL,'etag':ETAG,'output':str(output)}
        request=cache/'range-request.json'
        request.write_text(json.dumps(spec),encoding='utf-8')
        subprocess.run(['pwsh','-NoProfile','-File',str(project/'code/fetch_http_range.ps1'),'-RequestFile',str(request)],check=True)
        ranges.append({'start':start,'end':end,'size':output.stat().st_size,'sha256':sha(output)})
        return output.read_bytes()
    tail=fetch(TOTAL-65557,TOTAL-1,'archive-tail')
    position=tail.rfind(b'PK\x05\x06')
    if position<0:
        raise ValueError('ZIP end record absent')
    signature,disk,cd_disk,count_disk,count,size,offset,comment=struct.unpack_from('<4s4H2IH',tail,position)
    if disk or cd_disk or count_disk!=count or count==65535 or position+22+comment!=len(tail):
        raise ValueError('Unsupported or malformed end record')
    entries=central_directory(fetch(offset,offset+size-1,'archive-directory'))
    if len(entries)!=count:
        raise ValueError('Directory entry count differs')
    candidates=[e for e in entries if 'office' in e['name'].lower() and 'buildingpermit' in e['name'].lower()
        and 'terrain' not in e['name'].lower() and 'as-built' not in e['name'].lower() and (
        e['name'].lower().endswith('.ifc') or
        (e['name'].lower().endswith('.pdf') and 'specification' in e['name'].lower()))]
    extracted=[]
    if args.extract_office:
        for index,entry in enumerate(candidates):
            if entry['flags']&1 or entry['method'] not in (0,8) or entry['size']>400_000_000:
                raise ValueError('Unsupported or oversized selected source')
            local=fetch(entry['local_offset'],entry['local_offset']+29,f'local-header-{index}')
            values=struct.unpack('<4s5H3I2H',local)
            if values[0]!=b'PK\x03\x04' or values[3]!=entry['method']:
                raise ValueError('Local header incompatible with directory')
            start=entry['local_offset']+30+values[-2]+values[-1]
            compressed=fetch(start,start+entry['compressed_size']-1,f'office-compressed-{index}')
            content=zlib.decompress(compressed,-15) if entry['method']==8 else compressed
            if len(content)!=entry['size'] or (zlib.crc32(content)&0xffffffff)!=entry['crc32']:
                raise ValueError('Extracted source size/CRC mismatch')
            destination=cache/'sources'/PurePosixPath(entry['name'].replace('\\','/'))
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(content)
            extracted.append({**entry,'path':str(destination),'sha256':sha(destination)})
    result={'artifact_type':'selective_official_architecture_download','status':'SELECTED_SOURCES_CRC_VERIFIED' if extracted else 'DIRECTORY_ONLY',
        'url':URL,'publisher_page':'https://www.nordicsustainableconstruction.com/knowledge/2024/august/bim4lca-files',
        'archive_size':TOTAL,'etag':ETAG,'last_modified_head':'Thu, 15 Aug 2024 13:23:02 GMT','ranges':ranges,
        'codeSha256':sha(Path(__file__)),'transportHelperSha256':sha(project/'code/fetch_http_range.ps1'),
        'entry_count':len(entries),'office_candidates':candidates,'selected_sources':extracted,
        'limitations':['Partial archive retrieval binds ETag and byte ranges; complete archive SHA256 not available.',
            'Source CRC/size/SHA256 does not establish MEP/architecture coordinate alignment.']}
    folder=project/'milestones/reproducibility'
    (folder/'architecture-source-index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
    print(json.dumps({'status':result['status'],'entry_count':len(entries),'candidates':candidates,
        'selected':[{'name':e['name'],'size':e['size'],'sha256':e['sha256']} for e in extracted],
        'downloaded_bytes':sum(r['size'] for r in ranges)},ensure_ascii=True,indent=2))


if __name__=='__main__':
    main()
