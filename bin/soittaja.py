#!/usr/bin/env python3
#
# Lukee ts:ää enigma2:lta ja lähettää selaimelle HLS:nä. jos lähetyksen ääniraidat muuttuu, ffmpeg käynnistetään uudelleen
# uusilla raita-mäppäyksillä
#
# !TODO 
# -ffmpeg deinterlace
# -ffmpeg quiet
# -ts tunnista raitojen kielikoodi
# -varmista uudelleenkäynnistys striimin muuttuessa
# -valvo ettei ffmpeg jää jumiin
# -selaimen soittimen reboot (stuck kun framet ei lisäänny)
# -DVBSUB -> tesseract -> WEBVTT
#       
import threading
import requests
import sys
import time
import copy
import subprocess

FFCOMMAND="ffmpeg -loglevel quiet -re -i - %MAP -f hls -var_stream_map \"%VARSTREAMMAP\" -flags +cgop -g 25 -r 25 -c:v libx264 -b:v 8000k -c:a aac -b:a 96k -hls_flags delete_segments+append_list+omit_endlist -hls_time 1 -hls_list_size 10 -hls_segment_filename /dev/shm/hls/file_%v_%07d.ts /dev/shm/hls/out_%v.m3u8"
class Ffstriimaaja:
    def __init__(self):
        self.PATTABLE = {}
        self.CURTRACKS = {} #parhaillaan striimattavat raidat. kun lähetyksessä tämä muuttuu, striimaava ffmpeg uudelleenkäynnistetään
        self.LASTSEEN = {}
        self.PID = None
        self.PUSI = None
        self.Adaption = None
        self.pacno = 0
        self.th_e2lukija=threading.Thread(target=self.e2lukija)
        self.th_e2lukija.start()
        self.th_ffkirjoittaja=None
        self.prosff=None
        self.ffaja=True

    def parsePAT(self):
        start = 4
        stream_id = self.spacket[start]
        section_syntax_indicator = (self.spacket[start+1] & 0b10000000) >> 7
        section_syntax_indicator = self.spacket[start+1] & 0b10000000 >> 7
        section_length = int.from_bytes(self.spacket[start+2:start+4], byteorder='big') & 0b0000111111111111
        table_id_extension = int.from_bytes(self.spacket[start+4:start+6], byteorder='big')
        version_number = (self.spacket[start+6] & 0b00111110) >> 1
        current_next_indicator = (self.spacket[start+6] & 0b00000001)
        last_section_number = self.spacket[start+7]
        program_info_length = int.from_bytes(self.spacket[start+11:start+13], byteorder='big') & 0b0000111111111111
        proginfo = self.spacket[start+14:start+14+program_info_length]
        pointer = 17
        while pointer < section_length+4: 
            program_num = int.from_bytes(self.spacket[pointer:pointer+2], byteorder='big')
            program_map_pid = int.from_bytes(self.spacket[pointer+2:pointer+4], byteorder='big') & 0b0001111111111111
            self.PATTABLE[program_map_pid]=program_num
            self.LASTSEEN[program_map_pid]=time.time()
            #print(hex(program_num), "-->", hex(program_map_pid))
            pointer += 4

    def parsePES(self):
        start = 4
        stream_id = self.spacket[start]
        tableid = self.spacket[start]
        section_syntax_indicator = (self.spacket[start+1] & 0b10000000) >> 7
        private_indicator = (self.spacket[start+1] & 0b01000000) >> 6
        program_info_length = int.from_bytes(self.spacket[start+11:start+13], byteorder='big') & 0b0000111111111111
        section_length = int.from_bytes(self.spacket[start+2:start+4], byteorder='big') & 0b0000111111111111
        table_id_extension = int.from_bytes(self.spacket[start+4:start+6], byteorder='big')
        version_number = (self.spacket[start+6] & 0b00111110) >> 1
        current_next_indicator = (self.spacket[start+6] & 0b00000001)
        section_number = self.spacket[start+7]
        last_section_number = self.spacket[start+7]
        proginfo = self.spacket[start+14:start+14+program_info_length]

        if self.PID in self.PATTABLE: #Tämä on PMT-paketti!
            #print("***",self.PID)
            tracks_start_point = program_info_length+17
            pointer = tracks_start_point
            nytTracks={}
            while pointer < section_length+program_info_length: 
                # ISO/IEC 13818-1 : 2000 (E): Table 2-29 – Stream type assignments 2VIDEO 3AUDIO
                streamType = self.spacket[pointer]
                elementary_PID = int.from_bytes(self.spacket[pointer+1:pointer+3], byteorder='big') & 0b0001111111111111
                ES_info_length = int.from_bytes(self.spacket[pointer+3:pointer+5], byteorder='big') & 0b0000111111111111
                if streamType == 2 or streamType == 3: #video tai audio
                    #print("TYPE", hex(streamType), hex(elementary_PID))
                    nytTracks[elementary_PID]=streamType
                    #!TODO tässä käy läpi ES_info_length:n määrä loopilla!! pitäisi mm kielikoodi löytyä!
                pointer += ES_info_length+5
            if nytTracks != self.CURTRACKS: #raidat muuttuneet!
                print("MUUTOS oli",self.CURTRACKS,len(self.CURTRACKS))
                print("MUUTOS on",nytTracks)
                time.sleep(2)
                if self.th_ffkirjoittaja is not None: #ffkirjoittaja on olemassa joten tapetaan se ensin
                    print("Tapetan vanha")
                    self.ffaja=False
                    self.PATTABLE = {}
                    self.CURTRACKS = {}
                    self.LASTSEEN = {}
                    time.sleep(1)
                    self.th_ffkirjoittaja.join()
                self.th_ffkirjoittaja=threading.Thread(target=self.ffkirjoittaja)
                self.th_ffkirjoittaja.start()
                self.CURTRACKS = copy.deepcopy(nytTracks)
            # print(self.CURTRACKS)
            # print(nytTracks)

    def ffkirjoittaja(self): #kirjoita ffmpegillä out
        print("FFKIRJ")
        mappays=""
        varstreammap="v:0"
        MASTERPL="#EXTM3U\n#EXT-X-VERSION:3\n"
        atrcount=0
        for i in self.CURTRACKS:
            print("mäpätään",i, self.CURTRACKS[i])
            mappays+=" -map i:"+str(i)
            if self.CURTRACKS[i] != 2: #audiot..
                varstreammap+=" a:"+str(atrcount)
                lang="fin"
                name="finnish"
                if atrcount==0:
                    asel="YES"
                else:
                    asel="NO"
                trnum=str(atrcount+1)
                print("ADDAUD")
                MASTERPL+='#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aac",LANGUAGE="'+lang+'",NAME="'+name+'",DEFAULT=YES,AUTOSELECT='+asel+',URI="out_'+trnum+'.m3u8"\n'
                atrcount+=1
        MASTERPL+='#EXT-X-STREAM-INF:BANDWIDTH=2962000,NAME="Main",CODECS="avc1.66.30",RESOLUTION=1280x720,AUDIO="aac"\n'
        MASTERPL+="out_0.m3u8"
        with open("/dev/shm/hls/master.m3u8", "w") as mf:
            mf.write(MASTERPL)
       
        mappays=mappays[1:]
        ffcmd=FFCOMMAND.replace("%MAP",mappays)
        ffcmd=ffcmd.split(" ")
        for f in range(len(ffcmd)):
            if ffcmd[f]=='"%VARSTREAMMAP"':
                ffcmd[f]=varstreammap
        print(ffcmd)
        self.prosff=subprocess.Popen(ffcmd,stdin=subprocess.PIPE)
        self.ffaja=True
        while self.ffaja:
            time.sleep(0.3)
        self.prosff.kill()

    def ff_write_packet(self): #kirjoita yksittäinen ts-paketti ffmpegille
        #print(self.spacket)
        if self.ffaja and self.prosff is not None: #jos ffprosessi on käynnissä
            self.prosff.stdin.write(self.spacket)


    def e2lukija(self):
        self.url="http://192.168.1.12:8001/1:0:1:21:1001:20F6:EEEE0000:0:0:0:"
        self.spacket = None
        r = requests.get(self.url, stream=True) #HTTP
        r.raw #HTTP
        for self.spacket in r.iter_content(chunk_size=188):
            if self.spacket:
                if self.spacket[0] != 0x47:  # pitäisi olla aina 0x47 jos synkronointi pysynyt ok
                    print("sync fail")
                    sys.exit(1)
                else:
                    self.PUSI = (self.spacket[1] & 0b01000000) >> 6
                    self.TransportPriority = (self.spacket[1] >> 1) & 1
                    self.PID = int.from_bytes(self.spacket[1:3], byteorder='big') & 0b0001111111111111
                    self.Adaption = ((self.spacket[3]) & 0b00110000) >> 4
                    if self.PUSI != 0:
                        self.parsePES()
                    if self.PID == 0:
                        self.parsePAT()
                    self.pacno += 1
                self.ff_write_packet()

    def restartff(self):
        pass

    def terminateff(self):
        pass

if __name__ == "__main__":
    fstriimaaja=Ffstriimaaja()

    while True:
        #print("main")
        time.sleep(2)