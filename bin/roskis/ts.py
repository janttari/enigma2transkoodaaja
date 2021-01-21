#!/usr/bin/env python3
import requests
import requests
import sys
import time

url = 'http://192.168.1.12:8001/1:0:1:11:1001:20F6:EEEE0000:0:0:0:'


spacket = None
r = requests.get(url, stream=True) #HTTP
r.raw #HTTP

PATTABLE = {}
LASTSEEN ={} #jotta oidaan poistaa kun raita poistuu lähetyksestä
PID = None
PUSI = None
Adaption = None
pacno = 0


def parsePAT():
    start = 4
    stream_id = spacket[start]
    section_syntax_indicator = (spacket[start+1] & 0b10000000) >> 7
    section_syntax_indicator = spacket[start+1] & 0b10000000 >> 7
    section_length = int.from_bytes(
        spacket[start+2:start+4], byteorder='big') & 0b0000111111111111
    table_id_extension = int.from_bytes(
        spacket[start+4:start+6], byteorder='big')
    version_number = (spacket[start+6] & 0b00111110) >> 1
    current_next_indicator = (spacket[start+6] & 0b00000001)
    last_section_number = spacket[start+7]
    program_info_length = int.from_bytes(
        spacket[start+11:start+13], byteorder='big') & 0b0000111111111111
    proginfo = spacket[start+14:start+14+program_info_length]
    pointer = 17
    while pointer < section_length+4: 
        program_num = int.from_bytes(
            spacket[pointer:pointer+2], byteorder='big')
        program_map_pid = int.from_bytes(
            spacket[pointer+2:pointer+4], byteorder='big') & 0b0001111111111111
        PATTABLE[program_map_pid]=program_num
        LASTSEEN[program_map_pid]=time.time()
        #print(hex(program_num), "-->", hex(program_map_pid))
        pointer += 4

def parsePES():
    start = 4
    stream_id = spacket[start]
    tableid = spacket[start]
    section_syntax_indicator = (spacket[start+1] & 0b10000000) >> 7
    private_indicator = (spacket[start+1] & 0b01000000) >> 6
    program_info_length = int.from_bytes(
        spacket[start+11:start+13], byteorder='big') & 0b0000111111111111
    section_length = int.from_bytes(
        spacket[start+2:start+4], byteorder='big') & 0b0000111111111111
    table_id_extension = int.from_bytes(
        spacket[start+4:start+6], byteorder='big')
    version_number = (spacket[start+6] & 0b00111110) >> 1
    current_next_indicator = (spacket[start+6] & 0b00000001)
    section_number = spacket[start+7]
    last_section_number = spacket[start+7]
    proginfo = spacket[start+14:start+14+program_info_length]

    if PID in PATTABLE: #Tämä on PMT-paketti!
        print("***",PID)
        tracks_start_point = program_info_length+17
        pointer = tracks_start_point
        while pointer < section_length+program_info_length: 
            # ISO/IEC 13818-1 : 2000 (E): Table 2-29 – Stream type assignments 2VIDEO 3AUDIO
            streamType = spacket[pointer]
            elementary_PID = int.from_bytes(
                spacket[pointer+1:pointer+3], byteorder='big') & 0b0001111111111111
            ES_info_length = int.from_bytes(
                spacket[pointer+3:pointer+5], byteorder='big') & 0b0000111111111111
            print("TYPE", hex(streamType), hex(elementary_PID))
            #!TODO tässä käy läpi ES_info_length:n määrä loopilla!!
            pointer += ES_info_length+5



# with open("/home/pulla/gstreamer/o.ts", "rb") as f: #FILE
#     r = f.read(4444000) #FILE
# ccount = -1 #FILE
for spacket in r.iter_content(chunk_size=188): #HTTP
#for s in range(0, len(r), 188): #FILE
#dd    spacket = r[s:s+188] #FILE
    if spacket:
        # print(packet[0])
        if spacket[0] != 0x47:  # pitäisi olla aina 0x47 jos synkronointi pysynyt ok
            #print("sync fail")
            sys.exit()
        else:
            # TEI = (spacket[1] >> 3) & 1
            #PUSI = (spacket[1] >> 2) & 1
            PUSI = (spacket[1] & 0b01000000) >> 6
            #PUSI=(spacket[1]&0b00000010) >>1
            TransportPriority = (spacket[1] >> 1) & 1
            #PID = ((spacket[1] & 0x1F) << 8) | spacket[2]
            PID = int.from_bytes(
                spacket[1:3], byteorder='big') & 0b0001111111111111
            #Adaption = (spacket[3] >> 4) & 3
            Adaption = ((spacket[3]) & 0b00110000) >> 4

            if PUSI != 0:
                pass
                # print("PUSI")
                parsePES()
                #
            if PID == 0:
                pass
                parsePAT()
    pacno += 1
print("END")
