#!/usr/bin/env python3


# Testaillaan eri striimien raitoja tällä #


import time, copy

spacket=""
PATTABLE={}
CURTRACKS={}

STREAMTYPES={
0x0 :("Reserved", "-"),
0x1 :("MPEG-1 Video", "v"),
0x2 :("MPEG-2 Video", "v"),
0x3 :("MPEG-1 Audio", "a"),
0x4 :("MPEG-2 Audio", "a"),
0x5 :("ISO 13818-1 private sections", "-"),
0x6 :("Teletext or Subtitle", "s"), #0x6 :("ISO 13818-1 PES private data", "-"),
0x7 :("ISO 13522 MHEG", "-"),
0x8 :("ISO 13818-1 DSM-CC", "-"),
0x9 :("ISO 13818-1 auxiliary", "-"),
0xa :("ISO 13818-6 multi-protocol encap", "-"),
0xb :("ISO 13818-6 DSM-CC U-N msgs", "-"),
0xc :("ISO 13818-6 stream descriptors", "-"),
0xd :("ISO 13818-6 sections", "-"),
0xe :("ISO 13818-1 auxiliary", "-"),
0xf :("MPEG-2 AAC Audio", "a"),
0x10 :("MPEG-4 Video", "v"),
0x11 :("MPEG-4 LATM AAC Audio", "a"),
0x12 :("MPEG-4 generic", "-"),
0x13 :("ISO 14496-1 SL-packetized", "-"),
0x14 :("ISO 13818-6 Synchronized Download Protocol", "-"),
0x1b :("H.264 Video", "v"),
0x80 :("DigiCipher II Video", "v"),
0x81 :("A52/AC-3 Audio", "a"),
0x82 :("HDMV DTS Audio", "a"),
0x83 :("LPCM Audio", "a"),
0x84 :("SDDS Audio", "a"),
0x85 :("ATSC Program ID", "-"),
0x86 :("Hybridi", "-"), #0x86 :("DTS-HD Audio", "a"),
0x87 :("E-AC-3 Audio", "a"),
0x8a :("DTS Audio", "a"),
0x91 :("A52b/AC-3 Audio", "a"),
0x92 :("DVD_SPU vls Subtitle", "s"),
0x94 :("SDDS Audio", "a"),
0xa0 :("MSCODEC Video", "v"),
0xea :("Private ES (VC-1)", "-")
}


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
        PATTABLE[program_map_pid] = program_num
        pointer += 4

def parsePMT():
    if PID == 0: #onkin PAT
        return
    global PATTABLE, CURTRACKS
    start = 4
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
    print("SEC/LAST",PID, section_number,last_section_number)
    tracks_start_point = program_info_length+17
    pointer = tracks_start_point
    nytTracks = {}
    print("SPACNO:",spacno)
    while pointer < section_length+program_info_length-17:
        # ISO/IEC 13818-1 : 2000 (E): Table 2-29 – Stream type assignments 2VIDEO 3AUDIO
        streamType = spacket[pointer]
        elementary_PID = int.from_bytes(
            spacket[pointer+1:pointer+3], byteorder='big') & 0b0001111111111111
        ES_info_length = int.from_bytes(
            spacket[pointer+3:pointer+5], byteorder='big') & 0b0000111111111111
        lng="und"
        if streamType==3 or streamType== 0x11:
            for i in range(pointer,pointer+ES_info_length):
                if spacket[i] == 10 and spacket[i+1]==4:
                    try:
                        lng=spacket[i+2:i+5].decode()
                    except:
                        pass
        if streamType==6:
            ssubtype="-"
            for i in range(pointer,pointer+ES_info_length):
                try: #poikkeus jos onkin audio.. vittu mitä paskaa
                    if spacket[i]==0xE0 and spacket[i+1] == 0x44 and spacket[i+2] == 0x06:
                        streamType=0x87 
                        break
                except:
                    pass

                if spacket[i]==89 or spacket[i]==86: # and spacket[i+1]==4:
                    # try:
                    lng=spacket[i+2:i+5].decode()
                    subtype=spacket[i+5]
                    if subtype>=0x10 and subtype <= 0x14:
                        ssubtype="normal"
                    elif subtype>=0x20 and subtype <= 0x24:
                        ssubtype="hard of hearing"
                    if spacket[i]==86:
                        ssubtype="teletext" #teletext

                    # except:
                    #     pass
        print("TYPE", hex(streamType), hex(elementary_PID),lng,STREAMTYPES[streamType], end=" ")
        if streamType ==6:
            print("SUBTYPE:",ssubtype)
        else:
            print()
            # for o in range(pointer,pointer+15):
            #     print(int(spacket[o]),end=" ")
            # print()
        #ISO/IEC 13818-1 : 2000 Table 2-39 – Program and program element descriptors
        if streamType == 2 or streamType== 27 or streamType == 3 or streamType== 0x11:  # video tai audio
            nytTracks[elementary_PID] = [streamType,lng]
            #!TODO tässä käy läpi ES_info_length:n määrä loopilla!! pitäisi mm kielikoodi löytyä!
        pointer += ES_info_length+5
    
    if  nytTracks != CURTRACKS:  # raidat muuttuneet!
        print("RAIDAT MUUTTUNEET")
        CURTRACKS = copy.deepcopy(nytTracks)


if __name__ == "__main__":
    spacno=0
    with open("/home/pulla/Desktop/ts/yle1.ts", "rb") as f:
        while True:
            spacket = f.read(188)
            if not spacket:
                break
            if spacket[0] != 0x47:
                print("sync fail")
                sys.exit(1)
            PUSI = (spacket[1] & 0b01000000) >> 6
            TransportPriority = (spacket[1] >> 1) & 1
            PID = int.from_bytes(
            spacket[1:3], byteorder='big') & 0b0001111111111111
            Adaption = ((spacket[3]) & 0b00110000) >> 4
            if PUSI != 0 and PID in PATTABLE:
                print("PARSE PMT PID", PID)
                parsePMT()
            if PID == 0:
                parsePAT()
            spacno += 1
        