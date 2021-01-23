# e2transkoodaaja 
  
  ###e2transkoodaaja.py  
  Lukee striimiä enigma2-boksilta mäpäten siitä video- ja audioraidat  
  ja muuntaa sen ffmpegillä [HLS](https://en.wikipedia.org/wiki/HTTP_Live_Streaming)-muotoon  
  striimattavaksi.  

  www-hakemistossa on yksinkertainen [hls.js](https://github.com/video-dev/hls.js/)-pohjainen  
  soitin toistoa varten. Myös esimerkiksi [VLC](https://www.videolan.org/vlc/) osaa  
  toistaa tätä.  


    




![](https://raw.githubusercontent.com/janttari/enigma2transkoodaaja/main/DOC/kaavio.png)  


Aivan alkutekijöissään vielä :D  
Kaatuu mm. raitojen tunnistuksessa toisinaan.  
  
  
Idea on tunnistaa enigma2:n striimistä PAT-paketti ja sen perusteella PMT-paketti.  
Kun PMT-paketti löytyy (tai muuttuu), valitaan siitä edelleen striimattavat raidat  
ja aletaan Ffmpegillä striimaamaan ne HLS-muotoon.  
  



TODO:  ks bin/e2transkoodaaja.py !TODO  






kiitokset/ lähteet:  
https://github.com/tsduck/tsduck  
https://github.com/vguzov/videoio  
https://en.wikipedia.org/wiki/MPEG_transport_stream  
https://ecee.colorado.edu/~ecen5653/ecen5653/papers/iso13818-1.pdf  
http://happy.emu.id.au/lab/tut/dttb/dttbtuti.htm  
http://www.jeh-tech.com/mpeg.html  
https://www.programmersought.com/article/69414648609/  
https://www.ramugedia.com/python-scripts-to-analyze-and-process-transport-stream  


