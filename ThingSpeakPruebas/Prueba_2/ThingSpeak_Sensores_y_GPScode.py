from __future__ import print_function
import paho.mqtt.publish as publish
from time import sleep
import smbus,serial,time
import sys

## ------------------------ Inclusion of Own Headers ------------------------##
import HDC1080_Lib
import LTR390_Lib
import GPSProx_Lib

################################################################################
#------------------------------------------------------------------------------#

channelID = "1497567"  #Enter your Channel ID here

apiKey = "NEIDSS2DZHB3PS3W "  #Enter your WriteAPI key here


useUnsecuredTCP = False

useUnsecuredWebsockets = False

useSSLWebsockets = True


mqttHost = "mqtt.thingspeak.com"


if useUnsecuredTCP:
    tTransport = "tcp"
    tPort = 1883
    tTLS = None

if useUnsecuredWebsockets:
    tTransport = "websockets"
    tPort = 80
    tTLS = None

if useSSLWebsockets:
    import ssl
    tTransport = "websockets"
    tTLS = {'ca_certs':"/etc/ssl/certs/ca-certificates.crt",'tls_version':ssl.PROTOCOL_TLSv1}
    tPort = 443
        
topic = "channels/" + channelID + "/publish/" + apiKey

################################################################################
#------------------------------------------------------------------------------#

# Main Program

state=0

sen_hdc1080 = HDC1080_Lib.Sensor_HDC1080
sen_ltr390  = LTR390_Lib.Sensor_LTR390
GPS_Proximidad = GPSProx_Lib.GPS_Prox 


#Set GPIO Pins
GPIO_TRIGGER_d = 16 # GPIO 23
GPIO_ECHO_d = 18 # GPIO 24


ser = serial.Serial("/dev/ttyAMA0",9600)


temp = ""
humidity = ""

################################################################################
#------------------------------------------------------------------------------#
x = 1
while(x == 1):
    print(state)

 #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
 #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    if(state==0):#Colocar los vectores en cero
        
        Temp_data=[]
        Hum_data=[]
        ALS_data=[]
        UV_data=[]
        Prox_1_data=0

        state=2
 #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    
 #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~  
    elif(state==2): #Tomar 30 datos continuos de los sensores(rad y TempHum)
        
        for i in range(30):
            Temp_data.append(sen_hdc1080.read_Temperature())
            Hum_data.append(sen_hdc1080.read_Humidity())
            ALS_data.append(sen_ltr390.read_ambient_light())
            UV_data.append(sen_ltr390.read_radiation_UV())
        state=3
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
    elif(state==3):#Tomar dato de proximidad

        Prox_1_data=(GPS_Proximidad.distance(GPIO_TRIGGER_d,GPIO_ECHO_d))   
        print("Listo dato de Proximidad",Prox_1_data)
        ready_GPS=0
        state=4
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   
    elif(state==4):#Adquirir dato de GPS
        received_data = ser.readline()
        GPS_data = str(received_data)
        ready_GPS=GPS_Proximidad.conetion_GPS(GPS_data)

        if(ready_GPS==0):
            GPS_data_divide=["0","0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"]

            Data_W_Temp=0
            Data_W_Hum=0
            Data_W_ALS=0
            Data_W_UV=0
            Data_W_Prox1=0

            state=5

            
        else:
            if GPS_data[2:9] == "$GPRMC,":
                print(GPS_data)
                GPS_data_divide = GPS_Proximidad.sym_to_text(GPS_data)
                 
                Data_W_Temp=0
                Data_W_Hum=0
                Data_W_ALS=0
                Data_W_UV=0
                Data_W_Prox1=0

                state=5
            else:
                state=4
               
        
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   
    elif(state==5): #Calcular el promedio de los datos
        
        for i in range(30):
            Data_W_Temp +=Temp_data[i]
            Data_W_Hum +=Hum_data[i]
            Data_W_ALS +=ALS_data[i]
            Data_W_UV  +=UV_data[i]
        
        Data_W_Temp=round(Data_W_Temp/30,3)
        Data_W_Hum=round(Data_W_Hum/30,3)
        Data_W_ALS=round(Data_W_ALS/30,3)
        Data_W_UV=round(Data_W_UV/30,3)
        Data_W_Prox1=round(Prox_1_data,3)
    
        if(Data_W_Hum >= 85):
            sen_hdc1080.Turn_ON_Heater()
        else:
            sen_hdc1080.Turn_OFF_Heater()

        state=6

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~   
    elif(state==6): #Imprimir datos en la terminal

        print("-----------------------------------------------------------------------------------")
        print("          Toma de datos --> "+ time.strftime("%Y-%m-%d %H:%M:%S")+"\n") 
        print("Fecha = " + GPS_data_divide[13]+ "/" + GPS_data_divide[14] + "/" + GPS_data_divide[15])
        print("Hora="+ GPS_data_divide[0] + ":" + GPS_data_divide[1]  + ":" + GPS_data_divide[2])
        print("Latitud = " + GPS_data_divide[3] + "° " + GPS_data_divide[4] + "'" + GPS_data_divide[5] + "." + GPS_data_divide[6] + GPS_data_divide[7])
        print("Longitud = " + GPS_data_divide[8] + "° " + GPS_data_divide[9] + "'" + GPS_data_divide[10] + "." + GPS_data_divide[11] + "," + GPS_data_divide[12]+"\n")
        
        print("Distancia                 = ", Data_W_Prox1, " [cm]")
        print("Temperatura Ambiente      = ", Data_W_Temp, " [ºC]")
        print("Humedad Relativa del aire = ", Data_W_Hum, " [%]")
        print("Luz Ambiente              = ", Data_W_ALS, " [lux]")
        print("Radiación UV              = ", Data_W_UV, " [nW/cm^2]")

        print("-----------------------------------------------------------------------------------") 
        
        rev_Hum=sen_hdc1080.read_Humidity()
        if(rev_Hum >= 85):
            sen_hdc1080.Turn_ON_Heater()
        else:
            sen_hdc1080.Turn_OFF_Heater()

        state=7

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    elif(state==7): #Imprimir datos en ThingSpeak

        tPayload = "field1=" + str(Data_W_Temp) + "&field2=" + str(Data_W_Hum) + "&field3=" + str(Data_W_ALS)+ "&field4=" + str(Data_W_Prox1)+"&field5=" + GPS_data_divide[3] + "° " + GPS_data_divide[4] + "'" + GPS_data_divide[5] + "." + GPS_data_divide[6] + GPS_data_divide[7]+"&field6="+GPS_data_divide[8] + "° " + GPS_data_divide[9] + "'" + GPS_data_divide[10] + "." + GPS_data_divide[11] + "," + GPS_data_divide[12]

        try:
            publish.single(topic, payload=tPayload, hostname=mqttHost, port=tPort, tls=tTLS, transport=tTransport)
            state=0
            x=0
        except (KeyboardInterrupt):
            break

        except:
            print ("There was an error while publishing the data.")



#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~           
    else:
        state=state
