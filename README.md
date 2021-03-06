# e2transkoodaaja 
  
  ### e2transkoodaaja.py  
  Lukee striimiä enigma2-boksilta mäpäten siitä video- ja audioraidat  
  ja muuntaa sen ffmpegillä [HLS](https://en.wikipedia.org/wiki/HTTP_Live_Streaming)-muotoon  
  striimattavaksi.  

  www-hakemistossa on yksinkertainen [hls.js](https://github.com/video-dev/hls.js/)-pohjainen  
  soitin toistoa varten. Myös esimerkiksi [VLC](https://www.videolan.org/vlc/) osaa  
  toistaa tätä.  
  www-palvelimeksi suositeltava on [NGINX](https://www.nginx.com/).


---
### PERUSKÄYTTÖ:
```
./e2transkoodaaja.py ch1 create #luo kanavan nimeltä ch1  
./e2transkoodaaja.py ch1 e2play http://192.168.1.12:8001/1:0:1:51:1001:20F6:EEEE0000:0:0:0: #lähettää striimauspyynnön
./e2transkoodaaja.py ch1 delete #lopettaa kanavan
```



-----




![](https://raw.githubusercontent.com/janttari/enigma2transkoodaaja/main/DOC/kaavio.png)  


Aivan alkutekijöissään vielä :D  
Kaatuu mm. raitojen tunnistuksessa toisinaan.  
  
  
Idea on tunnistaa enigma2:n striimistä PAT-paketti ja sen perusteella PMT-paketti.  
Kun PMT-paketti löytyy (tai muuttuu), valitaan siitä edelleen striimattavat raidat  
ja aletaan Ffmpegillä striimaamaan ne HLS-muotoon.  
  



TODO:  ks [bin/e2transkoodaaja.py](bin/e2transkoodaaja.py)  



NGINX:lle seuraava asetus:
```
        location /hls {
            root /dev/shm;
            add_header Cache-Control no-cache;
            # dav_methods PUT DELETE MKCOL;
            # create_full_put_path  on;
            # dav_access all:rw;
        }
```





kiitokset/ lähteet:  
https://github.com/tsduck/tsduck  
https://github.com/vguzov/videoio  
https://en.wikipedia.org/wiki/MPEG_transport_stream  
https://ecee.colorado.edu/~ecen5653/ecen5653/papers/iso13818-1.pdf  
http://happy.emu.id.au/lab/tut/dttb/dttbtuti.htm  
http://www.jeh-tech.com/mpeg.html  
https://www.programmersought.com/article/69414648609/  
https://www.ramugedia.com/python-scripts-to-analyze-and-process-transport-stream  


