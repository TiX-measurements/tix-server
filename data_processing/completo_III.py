#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-
#
#!/usr/bin/env ipython-2.7
#
#
# Descripci贸n del script
# SALIDAS
# Este script genera como salida 4 archivos, por cada caso de entrada: caso 'l' y caso 'u'.
# Salida 1
# utilizacionInstantaneaUpstream
# Salida 2
# utilizacionInstantaneaDownstream
# Salida 3 - salida de 4 columnas: tiempo, util, H_rs, H_wavelet
# utilizacionUpstream			<- acumulando cada una hora y luego cada 5 minutos
# parametroHurstUpstreamRs		<- acumulando cada una hora y luego cada 5 minutos
# parametroHurstUpstreamWavelet	<- acumulando cada una hora y luego cada 5 minutos
# Salida 4 - salida de 4 columnas: tiempo, util, H_rs, H_wavelet
# utilizacionDownstream				<- acumulando cada una hora y luego cada 5 minutos
# parametroHurstDownstreamRs		<- acumulando cada una hora y luego cada 5 minutos
# parametroHurstDownstreamWavelet	<- acumulando cada una hora y luego cada 5 minutos
#
# Tambien se puede visualizar la sincronizacion de relojes en caso de ser necesario
# ENTRADAS
# Debe haberse ejecutado previamente el script 'estimaciones.py'. Necesita leer los datos de entrada generados por 'conversion_salida.py'y luego de ejecutar 'estimaciones.py' los siguientes valores para cada caso:
# C_AB o CA segun ecuaciones de TiX
# C_BA o CB segun ecuaciones de TiX
# lambda_S
# lambda_L

#import pylab # comentar en la version produccion
import scipy
import scipy.optimize
import numpy
#import matplotlib.pyplot as plt # comentar en la versio硁 producco贸n
import os
import subprocess
import time
import sys
import random, string
import logging
import rollbar
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.queue_declare(queue='process')
logFilePath = '/var/tmp/tixUDPServerTiempos.log'
logger = logging.getLogger('completo_III')
hdlr = logging.FileHandler(logFilePath)
logger.setLevel(logging.DEBUG)
# create console handler and set level to debug
hdlr.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
# add formatter to ch
hdlr.setFormatter(formatter)
# add ch to logger
logger.addHandler(hdlr)
### KEEP

def resultados(file_name,leer,umbral_utiliz,umbral_H):
	# Tama帽os de paquetes definidos en 'udpClientTiempos.js'
	#l_S = (60+8+20)*8       # [bits] 60 Bytes datos UDP + 8 Bytes header UDP + 20 Bytes header IP = 88 bytes
	#l_L = (4262+8+3*20)*8   # [bits] 4262 Bytes datos UDP + 8 Bytes header UDP + 3*20 Bytes header IP (3 paquetes) = 4330 bytes
	l_S = (48+8+20)*8		# [bits] 48 Bytes datos UDP + 8 Bytes header UDP + 20 Bytes header IP = 75 bytes
	l_L = (4449+8+3*20)*8	# [bits] 4449 Bytes datos UDP + 8 Bytes header UDP + 3*20 Bytes header IP (3 paquetes) = 4517 bytes

	# Aca voy a almacenar informacion entre el archivo de datos y los calculos
	# clave: file_name
	# valores: [C_AB 贸 CA, C_BA 贸 CB, lambda_S, lambda_L]

	info_necesaria = {}

	# Verifico existencia de archivos y leo parametros de entrada
	##################################################################################################################################
	# Expresiones para calculo delay del canal
	# tau = 0.5*min[tT(i) - tqA - tqB - 2*l(i)/C_sim]
	# tau = 0.5*min[tT(i) - tqA - tqB - l(i)/CA - l(i)/CB]		Eq. (17) TiX
	##################################################################################################################################

	# Descripci贸n de la funci贸n de este script:
	# Condici贸n necesaria: recibe como datos de entrada el/los archivos generados por el script conversion_salida.py
	# Aquellos datos que no son necesarios como entrada para otro calculo se imprimen en el archivo de salida precedidos por el caracter #
	# Como salida devuelve los valores calculados de:
	# tT_S	# [useg] tiempo de transito para paquetes chicos
	# tH_S	# [useg] umbral de decision para paquetes encolados chicos
	# tT_L	# [useg] tiempo de transito para paquetes chicos grandes
	# tH_L	# [useg] umbral de decision para paquetes encolados grandes
	# porcentaje de paquetes encolados [%]
	# Csim
	# CAB
	# CBA
	# lambda_S
	# lambda_L

        ### Tiempos cortos y largos tiene un arreglo con enteros, con los tiempos de los paquetes cortos y largos
	# Tiempos cortos
	probes_short = []			# En este vector acumulo todos los tT de paquetes cortos para hacer el histograma
	# Tiempos largos
	probes_large = []			# En este vector acumulo todos los tT de paquetes largos para hacer el histograma

	indice=0
        # Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
	t2_t1_o=0 # 0h
	t3_t2_o=0 # 0h
	t4_t3_o=0 # 0h
	t1_o = 0 # 0h
	t1c  = 0 # 0h
	t2_o = 0 # 0h
	t2c  = 0 # 0h
	primero=False # 0h

	logger.info("checkpoint 3.2.1")
	for line in leer:
		if line[0] != '#':
			aux_00 = line.split('|')
	#       	 print "id:", i, ", Hora: ",data[1], ", longitud: ", data[2], ", t1: ", data[3], ", t2: ", data[4], ", t3: ", data[5], ", t4: ", data[6], '\n'
			#print aux_00
			num_sec = indice
			length  = float(aux_00[2])
			t1  = float(aux_00[3]) 
			t2  = float(aux_00[4]) 
			t3  = float(aux_00[5]) 
			t4  = float(aux_00[6].split('\n')[0]) 
			indice = indice +1
        		# Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
			if (t1 - t1_o < -43200000000 ) and primero: 
				print "DEBUG t1 negativo, t1 :"+str(t1)+"  t1_o:"+str(t1_o)
				t1_o = t1
				t1c  = t1c+float(86400000000)
				print t1+t1c
			else: 
				t1_o = t1
			if (t2 - t2_o < -43200000000 ) and primero: 
				print "DEBUG t2 negativo, t2 :"+str(t2)+"  t1_o:"+str(t2_o)
				t2_o = t2
				t2c  = t2c+float(86400000000)
				print t2+86400000000
			else: 
				t2_o = t2
			#logger.info("checkpoint 3.2.2")
			t1=t1+t1c
			t4=t4+t1c
			t2=t2+t2c
			t3=t3+t2c
			### FIN 0h
			t2_t1 = t2-t1
			t3_t2 = t3-t2
			t4_t3 = t4-t3
        		# Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
			#print "DEBUG  t2_t1 , t2_t1:"+str(t2_t1)+" t2_t1_o:"+str(t2_t1_o)+" t2_t1 - t2_t1_o:"+str(t2_t1 - t2_t1_o)
			#print "DEBUG  t3_t2 , t3_t2:"+str(t3_t2)+" t3_t2_o:"+str(t3_t2_o)+" t3_t2 - t3_t2_o:"+str(t3_t2 - t3_t2_o)
			#print "DEBUG  t4_t3 , t4_t3:"+str(t4_t3)+" t4_t3_o:"+str(t4_t3_o)+" t4_t3 - t4_t3_o:"+str(t4_t3 - t4_t3_o)
			#if (t2_t1 - t2_t1_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t2_t1 negativo, t2_t1:"+str(t2_t1)+" t2_t1_o:"+str(t2_t1_o)+" t2_t1 - t2_t1_o:"+str(t2_t1 - t2_t1_o)
			#	t2_t1_o = t2_t1
			#	print "t2_t1 + 86400000000 :"+str(t2_t1 + float(86400000000) )+" t2:"+str(t2)+" t1:"+str(t1)+" type(t2_t1)"+str(type(t2_t1))
			#	#t2_t1 = t2_t1 + 86400000000 # 1 dia en microsegundos
			#elif (t2_t1 - t2_t1_o > 43200000000)and primero:
			#	print "DEBUG  t2_t1 positivo, t2_t1:"+str(t2_t1)+" t2_t1_o:"+str(t2_t1_o)+" t2_t1 - t2_t1_o:"+str(t2_t1 - t2_t1_o)
			#	t2_t1_o = t2_t1
			#	t2_t1 = t2_t1 - 86400000000 # 1 dia en microsegundos
			#else:
			#	t2_t1_o = t2_t1
			#if (t3_t2 - t3_t2_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t3_t2 negativo, t3_t2:"+str(t3_t2)+" t3_t2_o:"+str(t3_t2_o)+" t3_t2 - t3_t2_o:"+str(t3_t2 - t3_t2_o)
			#	t3_t2_o = t3_t2
			#	#t3_t2 = t3_t2 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t3_t2_o = t3_t2
			#if (t4_t3 - t4_t3_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t4_t3 negativo, t4_t3:"+str(t4_t3)+" t4_t3_o:"+str(t4_t3_o)+" t4_t3 - t4_t3_o:"+str(t4_t3 - t4_t3_o)
			#	t4_t3_o = t4_t3
				#t4_t3 = t4_t3 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t4_t3_o = t4_t3
			primero=True
                        ######## FIN 0h #########
			prop=int(length)/1500
			length=length+prop*20
			#print length,prop
			#aux_00 = line.split(' ')
			##print aux_00
			#sec_num = aux_00[0]
			#interval = float(aux_00[1])
			#length = aux_00[2]
			#rtt = float(aux_00[3])
			#t1 = float(aux_00[4])
			#t2_t1 = float(aux_00[5])
			#t3_t2 = float(aux_00[6])
			#t4_t3 = float(aux_00[7].split('\n')[0])
			tT = t4_t3 + t2_t1		# tiempo de transito, Eq. (8) de TiX
			if length < 144:		# Se usa la etiqueta '40'; NO es el tama帽o real
				probes_short.append(tT)
			elif length > 144:		# Se usa la etiqueta '1500'; NO es el tama帽o real
				probes_large.append(tT)

	# Informacion para calcular el histograma
	tT_Smin = int(min(probes_short))
	tT_Smax = int(max(probes_short))
	logger.info("checkpoint 3.2.3")
	delta = 250
	bines = round((tT_Smax - tT_Smin)/delta,0)		# Los bines DEBE ser un entero
	paso = round((tT_Smax - tT_Smin) / bines, 2)		# El paso real del histograma, debido al bin entero
	histo = scipy.histogram(probes_short,bins=bines)

	# Salida del histograma
	frecuencias = histo[0]
	tiempos = histo[1]

        ### Listado de Frecuencias y tiempos del histograma
	lista_frecuencias = numpy.ndarray.tolist(frecuencias)		# lo convierto a un array para poder accederlo por indice
	lista_tiempos = numpy.ndarray.tolist(tiempos)				# lo convierto a un array para poder accederlo por indice

	logger.info("checkpoint 3.2.4")
	# Convierto el vector de tiempos a la misma longitud que el de frecuencias, calculando el punto de acumulacion en el punto medio del intervalo
	size_lista_tiempos = len(lista_tiempos)
	vector_tiempos = []
	for x in range(0,size_lista_tiempos - 1):
		aux = lista_tiempos[x]
		x_1 = aux + paso/2
		vector_tiempos.append(x_1)

	logger.info("checkpoint 3.2.5")
	#Entradas para hacer las estimaciones 
	P_max = max(frecuencias)
	indice_t_Pmax = lista_frecuencias.index(P_max)

	t_first = vector_tiempos[0]
	t_Pmax = vector_tiempos[indice_t_Pmax]
	desvio = max(delta,(t_Pmax - t_first))

	# Truncamiento de la informaci贸n
	limite_truncamiento = t_Pmax + 3*desvio #3*desvio
	#print "desvio: "+str(desvio)+"  t_Pmax: "+str(t_Pmax)+"  limite_truncamiento: "+str(limite_truncamiento)#+"  vector_tiempos: "+str(vector_tiempos) 

        ### Trunca todos los tiempos 
	# Almaceno en este vector los tiempos truncados
	tiempos_truncados = []		
	for t in vector_tiempos:
		if t <= limite_truncamiento:
			tiempos_truncados.append(t)
	#print "len(tiempos_truncados): "+str(len(tiempos_truncados))

	# Documentacion de scipy - define a gaussian fitting function where:
	# p[0] = amplitude
	# p[1] = mean
	# p[2] = sigma
	fitfunc = lambda p, x: p[0]*scipy.exp(-(x-p[1])**2/(2.0*p[2]**2))
	errfunc = lambda p, x, y: fitfunc(p,x)-y

	# guess some fit parameters
	p0 = scipy.c_[P_max, t_Pmax, desvio]
	logger.info( "linea 251: pmax: %s tpmax: %s, desvio: %s" % (P_max, t_Pmax, desvio) )
	logger.info( "### frecuencias: %s" % (frecuencias) )
	logger.info( "### tiempos: %s" % (tiempos) )

	# Se hace el ajuste para diferentes cantidad de tiempos y se elije el ajuste de menor cv
	almaceno_tiempos = {}
	almaceno_cv = {}
	almaceno_estimadores = {}
	# Ajustes para diferentes series
	rango_ajuste = range(indice_t_Pmax + 1, len(tiempos_truncados))
	#rango_ajuste = range(len(tiempos_truncados) , len(tiempos_truncados)+1)
	#print rango_ajuste
	logger.info("checkpoint 3.2.5")
	log_file_name_hist =  open('log_histo' + file_name + ".log" ,"w")
	for el in rango_ajuste:
		xcorr = vector_tiempos[0:el+1]
		ycorr = lista_frecuencias[0:len(xcorr)]
		almaceno_tiempos[el] = xcorr

		# fit a gaussian
                try: 
			logger.info("checkpoint 3.2.5.1 p0size:%s xcorr:%s ycorr:%s" % (len(p0[0]), len(xcorr), len(ycorr)))
			logger.info("p0.copy()[0]:%s" % (p0.copy()[0]))

			#logging into file
			log_file_name_hist.write("p0.copy()[0]:%s\n" % (p0.copy()[0]))
 			log_file_name_hist.write("#####xcorr\n")
			for item in xcorr:
				log_file_name_hist.write("%s," % item)
			log_file_name_hist.write("\n")
                        log_file_name_hist.write("#####ycorr\n")
			for ite2 in ycorr:
				log_file_name_hist.write("%s," % ite2)
			log_file_name_hist.write("\n\n")

                        log_file_name_hist.write("#####about to run leastsq\n")

			log_file_name_hist.flush()

			p1, success = scipy.optimize.leastsq(errfunc, p0.copy()[0], args=(xcorr,ycorr))
			
                        log_file_name_hist.write("#####i just ran leastsq\n")
			
			logger.info("checkpoint 3.2.5.2")
                except: 
			logger.info("checkpoint 3.2.5.1e p0size: %s" % len(p0[0]))
			p1=p0.copy()[0]
			logger.info("checkpoint 3.2.5.2e")
			pass
		logger.info("checkpoint 3.2.5.3")
		almaceno_estimadores[el] = p1

		amp_estimada = p1[0]
		tiempo_estimado = p1[1]
		dsv_estimado = p1[2]

		# Calculo coeficiente de variacion
		cv = dsv_estimado/tiempo_estimado
		if cv > 0:
			almaceno_cv[cv] = el
		logger.info("checkpoint 3.2.5.4")
		#almaceno_cv[cv] = el
	
	log_file_name_hist.close()
	logger.info("checkpoint 3.2.6")
	# Ahora me quedo con el menor de los cv para calculos y graficos del ajuste
	indice_cv = almaceno_cv.keys()
	cv_min = min(indice_cv)
	elementos_tiempo = almaceno_cv[cv_min]

	p1 = almaceno_estimadores[elementos_tiempo]
	amp_estimada = p1[0]
	tiempo_estimado = p1[1]
	# SALIDA
	tT_S = tiempo_estimado
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [tT_S]
	else:
		aux = info_necesaria[file_name]
		aux.append(tT_S)
		info_necesaria[file_name] = aux
	#------------------------------------------
		
	dsv_estimado = p1[2]
	# Calculo umbral para paquetes encolados
	umbral_S = tiempo_estimado + 3* dsv_estimado
	# SALIDA
	tH_S = umbral_S
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [tH_S]
	else:
		aux = info_necesaria[file_name]
		aux.append(tH_S)
		info_necesaria[file_name] = aux
	#------------------------------------------
	# Calculo factor lambda para sync de relojes
	# SALIDA
	lambda_S = tH_S - tT_Smin
	#------------------------------------------
	logger.info("checkpoint 3.2.7")
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [lambda_S]
	else:
		aux = info_necesaria[file_name]
		aux.append(lambda_S)
		info_necesaria[file_name] = aux
	#------------------------------------------

	# Datos para el ajuste
	xcorr = almaceno_tiempos[elementos_tiempo]
	ycorr = lista_frecuencias[0:len(xcorr)]
	# Datos truncados	
	xrest = vector_tiempos[len(xcorr):len(vector_tiempos)]
	yrest = lista_frecuencias[len(ycorr):len(lista_frecuencias)]

	# Calculo porcentaje paquetes encolados
	pqTotal_S = len(probes_short)
	sq_S = 0	# SI encolados
	for p in probes_short:
		if p > umbral_S:
			sq_S = sq_S + 1

	#### Para graficar el histograma: descomentar las siguientes lineas 
	## Calculo los puntos de la funcion continua de ajuste
	#arreglo = numpy.arange(t_first, limite_truncamiento, 0.01)
	#fn_est = fitfunc(p1, arreglo)
	#plt.plot(xcorr,ycorr, 'go')
	#plt.plot(xcorr,ycorr, 'g-', label='Histograma')
	#plt.plot(xrest,yrest, 'bo')
	#plt.plot(xrest,yrest, 'b-', label='Truncamiento')
	#plt.plot(arreglo, fn_est,'r-', label='Funcion de ajuste')
	#plt.ylabel('Frecuencias')
	#plt.xlabel('tiempos [us]')
	#plt.title('Modelado de tiempos minimos cortos caso: '+file_name)
	#plt.grid(True)
	#plt.legend()
	#plt.show()
	##---------------------------------------------------------------
	################################################################
	# Comienzan los c谩lculos para paquetes grandes (L)
	tT_Lmin = int(min(probes_large))
	tT_Lmax = int(max(probes_large))

	delta = 250
	bines = round((tT_Lmax - tT_Lmin)/delta,0)		# DEBE ser entero
	paso = (tT_Lmax - tT_Lmin) / bines
	histo = scipy.histogram(probes_large,bins=bines)
	logger.info("checkpoint 3.2.8")

	frecuencias = histo[0]
	lista_frecuencias = numpy.ndarray.tolist(frecuencias)
	tiempos = histo[1]
	lista_tiempos = numpy.ndarray.tolist(tiempos)
	# Convierto el vector de tiempos a la misma longitud que el de frecuencias, graficando el punto de acumulacion en el punto medio del intervalo
	size_lista_tiempos = len(lista_tiempos)
	vector_tiempos = []
	for x in range(0,size_lista_tiempos - 1):
		aux = lista_tiempos[x]
		x_1 = round(aux + paso/2, 2)
		vector_tiempos.append(x_1)

	# Entradas para hacer las estimaciones
	t_first = vector_tiempos[0]
	P_max = max(frecuencias)
	indice_t_Pmax = lista_frecuencias.index(P_max)
	t_Pmax = vector_tiempos[indice_t_Pmax]
	desvio = max(delta,(t_Pmax - t_first))

	# Truncamiento
	limite_truncamiento = t_Pmax + 3*desvio #3*desvio
	tiempos_truncados = []
	for t in vector_tiempos:
	    if t <= limite_truncamiento:
		tiempos_truncados.append(t)

	# define a gaussian fitting function where
	# p[0] = amplitude
	# p[1] = mean
	# p[2] = sigma
	fitfunc = lambda p, x: p[0]*scipy.exp(-(x-p[1])**2/(2.0*p[2]**2))
	errfunc = lambda p, x, y: fitfunc(p,x)-y

	# guess some fit parameters
	p0 = scipy.c_[P_max, t_Pmax, desvio]
	logger.info( "linea 416:: pmax: %s tpmax: %s, desvio: %s" % (P_max, t_Pmax, desvio) )

	almaceno_tiempos = {}
	almaceno_cv = {}
	# Ajustes para diferentes series
	rango_ajuste = range(indice_t_Pmax + 1, len(tiempos_truncados))
	#rango_ajuste = range(len(tiempos_truncados), len(tiempos_truncados) + 1)
	for el in rango_ajuste:
	    xcorr = vector_tiempos[0:el+1]
	    ycorr = lista_frecuencias[0:len(xcorr)]
	    almaceno_tiempos[el] = xcorr

	    # fit a gaussian
            try: 
		p1, success = scipy.optimize.leastsq(errfunc, p0.copy()[0], args=(xcorr,ycorr))
            except: 
		p1=p0.copy()[0]
		pass
	    #p1=p0[0]
	    almaceno_estimadores[el] = p1

	    amp_estimada = p1[0]
	    tiempo_estimado = p1[1]
	    dsv_estimado = p1[2]

	    # Calculo coeficiente de variacion
	    cv = dsv_estimado/tiempo_estimado
	    if cv > 0:
		almaceno_cv[cv] = el

	# Ahora me quedo con el menor de los cv para calculos y graficos del ajuste
	indice_cv = almaceno_cv.keys()
	cv_min = min(indice_cv)
	elementos_tiempo = almaceno_cv[cv_min]

	p1 = almaceno_estimadores[elementos_tiempo]
	amp_estimada = p1[0]
	tiempo_estimado = p1[1]
	# SALIDA
	tT_L = tiempo_estimado
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [tT_L]
	else:
		aux = info_necesaria[file_name]
		aux.append(tT_L)
		info_necesaria[file_name] = aux
	#------------------------------------------

	dsv_estimado = p1[2]
	# Calculo umbral para paquetes encolados
	umbral_L = tiempo_estimado + 3* dsv_estimado
	# SALIDA
	tH_L = umbral_L
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [tH_L]
	else:
		aux = info_necesaria[file_name]
		aux.append(tH_L)
		info_necesaria[file_name] = aux
	#------------------------------------------
	# Calculo factor lambda para sync de relojes
	# SALIDA
	lambda_L = tH_L - tT_Lmin
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [lambda_L]
	else:
		aux = info_necesaria[file_name]
		aux.append(lambda_L)
		info_necesaria[file_name] = aux
	#------------------------------------------

	# Datos del ajuste
	xcorr = almaceno_tiempos[elementos_tiempo]
	ycorr = lista_frecuencias[0:len(xcorr)]
	# Datos truncados
	xrest = vector_tiempos[len(xcorr):len(vector_tiempos)]
	yrest = lista_frecuencias[len(ycorr):len(lista_frecuencias)]

	# Calculo porcentaje paquetes encolados
	pqTotal_L = len(probes_large)
	sq_L = 0	# SI encolados largos
	for p in probes_large:
		if p > umbral_L:
			sq_L = sq_L + 1
	pqTotales = pqTotal_S + pqTotal_L
	sq = sq_S + sq_L
	# SALIDA
	pq_queue = 100 * (float(sq)/pqTotales)
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [pq_queue]
	else:
		aux = info_necesaria[file_name]
		aux.append(pq_queue)
		info_necesaria[file_name] = aux
	#------------------------------------------

	#### Para graficar el histograma: descomentar las siguientes lineas 
	## Calculo los puntos de la funcion continua de ajuste
	## Para graficar el histograma
	#arreglo = numpy.arange(t_first, limite_truncamiento, 0.01)
	#fn_est = fitfunc(p1, arreglo)
	#plt.plot(xcorr,ycorr, 'go')
	#plt.plot(xcorr,ycorr, 'g-', label='Histograma')
	#plt.plot(xrest,yrest, 'bo')
	#plt.plot(xrest,yrest, 'b-', label='Truncamiento')
	#plt.plot(arreglo, fn_est,'r-', label='Funcion de ajuste')
	#plt.ylabel('Frecuencias')
	#plt.xlabel('tiempos [us]')
	#plt.title('Modelado de tiempos minimos largos caso '+file_name)
	#plt.grid(True)
	#plt.legend()
	#plt.show()
	##---------------------------------------------------------------
	################################################################

	# Calculo de la capacidad sim茅trica	con pares de valores t2, t1
	# Csim = 2*(l_L - l_S)/(tT_L - tT_S)	eq. (14) TiX
	for file_name in info_necesaria.keys():
		datos = info_necesaria[file_name]
		tT_S = datos[0]
		tT_L = datos[3]
		Csim = 2*(l_L - l_S)/(tT_L - tT_S)	# [bits]/[useg] = [Mbps]
		datos.append(Csim)
		#------------------------------------------
		info_necesaria[file_name] = datos
		#------------------------------------------
		
	# Calculo de la capacidad asimetrica usando la mediana como estimador
	# C = (l_L - l_S)/Mr    eq. (16) TiX
	datos = info_necesaria[file_name]
	tH_S = datos[1]
	tH_L = datos[4]

	t_no_encolados = []
	indice=1
        # Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
	t2_t1_o=0 # 0h
	t3_t2_o=0 # 0h
	t4_t3_o=0 # 0h
	t1_o = 0 # 0h
	t1c  = 0 # 0h
	t2_o = 0 # 0h
	t2c  = 0 # 0h
	primero=False # 0h
	for line in leer:
		if line[0] != '#':
			aux_00 = line.split('|')
			num_sec = indice
			length  = float(aux_00[2])
			t1  = float(aux_00[3])
			t2  = float(aux_00[4])
			t3  = float(aux_00[5])
			t4  = float(aux_00[6].split('\n')[0])
			rtt=0
        		# Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
			if (t1 - t1_o < -43200000000 ) and primero: 
				print "DEBUG t1 negativo, t1 :"+str(t1)+"  t1_o:"+str(t1_o)
				t1_o = t1
				t1c  = t1c+float(86400000000)
				print t1+t1c
			else: 
				t1_o = t1
			if (t2 - t2_o < -43200000000 ) and primero: 
				print "DEBUG t2 negativo, t2 :"+str(t2)+"  t1_o:"+str(t2_o)
				t2_o = t2
				t2c  = t2c+float(86400000000)
				print t2+86400000000
			else: 
				t2_o = t2
			t1=t1+t1c
			t4=t4+t1c
			t2=t2+t2c
			t3=t3+t2c
			### FIN 0h
			t2_t1 = t2-t1
			t3_t2 = t3-t2
			t4_t3 = t4-t3
        		# Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
			#if (t2_t1 - t2_t1_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t2_t1 negativo, t2_t1:"+str(t2_t1)+" t2_t1_o:"+str(t2_t1_o)+" t2_t1 - t2_t1_o:"+str(t2_t1 - t2_t1_o)
			#	t2_t1_o = t2_t1
			#	#t2_t1 = t2_t1 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t2_t1_o = t2_t1
			#if (t3_t2 - t3_t2_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t3_t2 negativo, t3_t2:"+str(t3_t2)+" t3_t2_o:"+str(t3_t2_o)+" t3_t2 - t3_t2_o:"+str(t3_t2 - t3_t2_o)
			#	t3_t2_o = t3_t2
				#t3_t2 = t3_t2 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t3_t2_o = t3_t2
			#if (t4_t3 - t4_t3_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t4_t3 negativo, t4_t3:"+str(t4_t3)+" t4_t3_o:"+str(t4_t3_o)+" t4_t3 - t4_t3_o:"+str(t4_t3 - t4_t3_o)
			#	t4_t3_o = t4_t3
			#	#t4_t3 = t4_t3 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t4_t3_o = t4_t3
			primero=True
                        ######## FIN 0h #########
			if indice == 1:
				interval = 0
				t1_anterior = t1
			else:
				interval = t1 - t1_anterior
				t1_anterior = t1
			indice = indice +1
			seq_num = float(indice)
			#valores = line.split(' ')
			#seq_num = float(valores[0])
			#interval = valores[1]
			#length = float(valores[2])
			#rtt = valores[3]
			#t1 = float(valores[4])
			#t2_t1 = float(valores[5])
			#t3_t2 = float(valores[6])
			#t4_t3 = float(valores[7].split('\n')[0])
			tT = t4_t3 + t2_t1
			componentes = (seq_num,interval,length,rtt,t1,t2_t1,t3_t2,t4_t3)
			if length < 144 :
				if tT < tH_S:
					t_no_encolados.append(componentes)
			elif length > 144:
				if tT < tH_L:
					t_no_encolados.append(componentes)

	# Busco paquetes entre los no encolados consecutivos de diferente tama帽o
	# Consecutivos: t_no_encolados[i][0] - t_no_encolados[i-1][0] = 0.5
	# Diferente tama帽o:  t_no_encolados[i][2] - t_no_encolados[i-1][2] = 1460.0
	data_AB = []	# t2,t1	=> upstream
	data_BA = []	# t4,t3 => downstream
	size_t_no_encolados = len(t_no_encolados)
	for i in range(1,size_t_no_encolados):
		diff_length = t_no_encolados[i][2] - t_no_encolados[i-1][2]
		if diff_length > 144:  # IMPORTANTE: no encolados
			diff_sec = t_no_encolados[i][0] - t_no_encolados[i-1][0]
			if diff_sec == 1:
				# Sentido subida
				t2_t1_actual = t_no_encolados[i][5]
				t2_t1_anterior = t_no_encolados[i-1][5]
				tiempos_AB = t2_t1_actual - t2_t1_anterior
				data_AB.append(tiempos_AB)
				# Sentido bajada
				t4_t3_actual = t_no_encolados[i][7]
				t4_t3_anterior = t_no_encolados[i-1][7]
				tiempos_BA = t4_t3_actual - t4_t3_anterior
				data_BA.append(tiempos_BA)

	# CALCULO SENTIDO AB	
	tAB_min = min(data_AB)
	tAB_max = max(data_AB)

	# HISTOGRAMA
	delta = 250
	bines = round((tAB_max - tAB_min)/delta,0)
	paso = (tAB_max - tAB_min) / bines
	histo = scipy.histogram(data_AB,bins=bines)

	frecuencias = histo[0]
	lista_frecuencias = numpy.ndarray.tolist(frecuencias)
	tiempos = histo[1]
	lista_tiempos = numpy.ndarray.tolist(tiempos)
	# Convierto el vector de tiempos a la misma longitud que el de frecuencias, graficando el punto de acumulacion en el punto medio del intervalo
	size_lista_tiempos = len(lista_tiempos)
	vector_tiempos = []
	for x in range(0,size_lista_tiempos - 1):
		aux = lista_tiempos[x]
		x_1 = aux + paso/2
		vector_tiempos.append(x_1)

	## Para graficar el histograma descomentar
	#x1 = vector_tiempos
	#y1 = frecuencias
	#plt.plot(x1,y1, 'go')
	#plt.plot(x1,y1, 'g-', label='Histograma')
	#plt.ylabel('Frecuencias')
	#plt.xlabel('tiempos [us]')
	#plt.title('Histograma para tiempos encolados')
	#plt.grid(True)
	#plt.legend()
	#plt.show()

	#Estimaciones
	t_first = vector_tiempos[0]
	P_max = max(frecuencias)
	indice_t_Pmax = lista_frecuencias.index(P_max)
	t_Pmax = vector_tiempos[indice_t_Pmax]
	desvio = max(delta,(t_Pmax - t_first))

	# Truncamiento
	limite_truncamiento = t_Pmax + 3*desvio
	tiempos_truncados = []
	for t in data_AB:
		if t <= limite_truncamiento:
			tiempos_truncados.append(t)

	# Mediana entre t_first y 2 desvios
	mediana = numpy.median(tiempos_truncados)
	# SALIDA
	M_AB = mediana
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [M_AB]
	else:
		aux = info_necesaria[file_name]
		aux.append(M_AB)
		info_necesaria[file_name] = aux
	#------------------------------------------
	# SALIDA
	C_AB = (l_L - l_S) / M_AB
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [C_AB]
	else:
		aux = info_necesaria[file_name]
		aux.append(C_AB)
		info_necesaria[file_name] = aux
	#------------------------------------------

	# CALCULO SENTIDO BA
	tBA_min = min(data_BA)
	tBA_max = max(data_BA)

	# HISTOGRAMA
	delta = 250
	bines = round((tBA_max - tBA_min)/delta,0)
	paso = (tBA_max - tBA_min) / bines
	histo = scipy.histogram(data_BA,bins=bines)

	frecuencias = histo[0]
	lista_frecuencias = numpy.ndarray.tolist(frecuencias)
	tiempos = histo[1]
	lista_tiempos = numpy.ndarray.tolist(tiempos)
	# Convierto el vector de tiempos a la misma longitud que el de frecuencias, graficando el punto de acumulacion en el punto medio del intervalo
	size_lista_tiempos = len(lista_tiempos)
	vector_tiempos = []
	for x in range(0,size_lista_tiempos - 1):
		aux = lista_tiempos[x]
		x_1 = aux + paso/2
		vector_tiempos.append(x_1)

	## Para graficar el histograma descomentar
	#x1 = vector_tiempos
	#y1 = frecuencias
	#plt.plot(x1,y1, 'go')
	#plt.plot(x1,y1, 'g-', label='Histograma')
	#plt.ylabel('Frecuencias')
	#plt.xlabel('tiempos [us]')
	#plt.title('Histograma para tiempos encolados')
	#plt.grid(True)
	#plt.legend()
	#plt.show()

	#Estimaciones
	t_first = vector_tiempos[0]
	P_max = max(frecuencias)
	indice_t_Pmax = lista_frecuencias.index(P_max)
	t_Pmax = vector_tiempos[indice_t_Pmax]
	desvio = max(delta,(t_Pmax - t_first))

	# Truncamiento
	limite_truncamiento = t_Pmax + 3*desvio
	tiempos_truncados = []
	for t in data_BA:
		if t <= limite_truncamiento:
			tiempos_truncados.append(t)

	# Mediana entre t_first y 2 desvios
	mediana = numpy.median(tiempos_truncados)
	# SALIDA
	M_BA = mediana
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [M_BA]
	else:
		aux = info_necesaria[file_name]
		aux.append(M_BA)
		info_necesaria[file_name] = aux
	#------------------------------------------
	# SALIDA
	C_BA = (l_L - l_S) / M_BA
	#------------------------------------------
	compara = info_necesaria.has_key(file_name)
	if compara == 0:
		info_necesaria[file_name] = [C_BA]
	else:
		aux = info_necesaria[file_name]
		aux.append(C_BA)
		info_necesaria[file_name] = aux
	#------------------------------------------

	# Escribo salida
	for file_name in info_necesaria.keys():
		datos = info_necesaria[file_name]
		# clave: file_name
		# valores: [tT_S, tH_S, lambda_S, tT_L, tH_L, lambda_L, %pq_queue, Csim, M_AB, C_AB, M_BA, C_BA]
		tT_S = round(datos[0], 3)
		tH_S = round(datos[1], 3)
		lambda_S = round(datos[2], 3)
		tT_L = round(datos[3], 3)
		tH_L = round(datos[4], 3)
		lambda_L = round(datos[5], 3)
		pq_queue = round(datos[6], 3)
		Csim = round(datos[7], 3)
		M_AB = round(datos[8], 3)
		C_AB = round(datos[9], 3)
		M_BA = round(datos[10], 3)
		C_BA = round(datos[11], 3)
		# Para escribir en el lugar correcto
		busco_caso = file_name.split('/')
		ip = busco_caso[len(busco_caso)-2]
		nombre = busco_caso[len(busco_caso)-1].split('_')[0]
		caso = busco_caso[len(busco_caso)-1].split('_')[1]
		if caso == 'l.txt':
			fsalida = nombre+'_l.calculos'
		elif caso == 'u.txt':
			fsalida = nombre+'_u.calculos'
		#path_dst = dir_base+ip+'/'
		#fsalida_abs = path_dst+fsalida
		#if os.path.isfile(fsalida_abs) == True:
		#	print 'Ya existe el archivo. Verificar si ya se hicieron los calculos.'
		#	break
                #####################################################################
		#  Escritura en archivo de salida
                #####################################################################
		#fsalida_abs=file_name+'.calculos' # IMPORTANTE: depende de la entrada 
		#f = open(fsalida_abs, 'w')
		#cadena_00 = '# tT_S = '+str(tT_S)+' useg\n'
		#f.write(cadena_00)
		#cadena_01 = '# tH_S = '+str(tH_S)+' useg\n'
		#f.write(cadena_01)
		#cadena_02 = '# tT_L = '+str(tT_L)+' useg\n'
		#f.write(cadena_02)
		#cadena_03 = '# tH_L = '+str(tH_L)+' useg\n'
		#f.write(cadena_03)
		#cadena_04 = '# Capacidad Simetrica = '+str(Csim)+' Mbps\n'
		#f.write(cadena_04)
		#cadena_05 = '# Porcentaje de paquetes encolados = '+str(pq_queue)+' %\n'
		#f.write(cadena_05)
		#cadena_06 = 'Capacidad Asimetrica (subida) = '+str(C_AB)+' Mbps\n'
		#f.write(cadena_06)
		#cadena_07 = 'Capacidad Asimetrica (bajada) = '+str(C_BA)+' Mbps\n'
		#f.write(cadena_07)
		#cadena_08 = 'Parametro lambda para sync relojes (paquetes chicos) = '+str(lambda_S)+' useg\n'
		#f.write(cadena_08)
		#cadena_09 = 'Parametro lambda para sync relojes (paquetes grandes) = '+str(lambda_L)+' useg\n'
		#f.write(cadena_09)
		## Cierro el archivo
		#f.close()
	##################################################################################################################################
	##################################################################################################################################

	datos_almacenados = {}
	indice_secuencias = []
	delay = []
	# Datos de capacidad para calcular los tiempos de insercion
	#datos_previos = info_necesaria[file_name]
	#CA = float(datos_previos[0])
	CA = C_AB
	#CB = float(datos_previos[1])
	CB = C_BA
	#
	# Umbrales para sync de relojes
	#lambda_S = float(datos_previos[2])
	#lambda_L = float(datos_previos[3])
	#
	indice=1
        # Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
	t2_t1_o=0 # 0h
	t3_t2_o=0 # 0h
	t4_t3_o=0 # 0h
	t1_o = 0 # 0h
	t1c  = 0 # 0h
	t2_o = 0 # 0h
	t2c  = 0 # 0h
	primero=False # 0h
	for line in leer:
		if line[0] != '#':
			aux_00 = line.split('|')
			num_sec = indice
			length  = float(aux_00[2])
			t1  = float(aux_00[3])
			t2  = float(aux_00[4])
			t3  = float(aux_00[5])
			t4  = float(aux_00[6].split('\n')[0])
			rtt=0
        		# Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
			if (t1 - t1_o < -43200000000 ) and primero: 
				print "DEBUG t1 negativo, t1 :"+str(t1)+"  t1_o:"+str(t1_o)
				t1_o = t1
				t1c  = t1c+float(86400000000)
				print t1+t1c
			else: 
				t1_o = t1
			if (t2 - t2_o < -43200000000 ) and primero: 
				print "DEBUG t2 negativo, t2 :"+str(t2)+"  t1_o:"+str(t2_o)
				t2_o = t2
				t2c  = t2c+float(86400000000)
				print t2+86400000000
			else: 
				t2_o = t2
			t1=t1+t1c
			t4=t4+t1c
			t2=t2+t2c
			t3=t3+t2c
			### FIN 0h
			t2_t1 = t2-t1
			t3_t2 = t3-t2
			t4_t3 = t4-t3
        		# Esto es para compensar el problema de las 0hs, que los contadores vuelven a comenzar JIAH : # 0h
			#if (t2_t1 - t2_t1_o < -43200000000) and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t2_t1 negativo, t2_t1:"+str(t2_t1)+" t2_t1_o:"+str(t2_t1_o)+" t2_t1 - t2_t1_o:"+str(t2_t1 - t2_t1_o)
			#	t2_t1_o = t2_t1
				#t2_t1 = t2_t1 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t2_t1_o = t2_t1
			#if (t3_t2 - t3_t2_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t3_t2 negativo, t3_t2:"+str(t3_t2)+" t3_t2_o:"+str(t3_t2_o)+" t3_t2 - t3_t2_o:"+str(t3_t2 - t3_t2_o)
			#	t3_t2_o = t3_t2
				#t3_t2 = t3_t2 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t3_t2_o = t3_t2
			#if (t4_t3 - t4_t3_o < -43200000000)and primero: # 0h, 43200000000 = 1/2 dia en microsegundos
			#	print "DEBUG  t4_t3 negativo, t4_t3:"+str(t4_t3)+" t4_t3_o:"+str(t4_t3_o)+" t4_t3 - t4_t3_o:"+str(t4_t3 - t4_t3_o)
			#	t4_t3_o = t4_t3
				#t4_t3 = t4_t3 + 86400000000 # 1 dia en microsegundos
			#else:
			#	t4_t3_o = t4_t3
			primero=True
                        ######## FIN 0h #########
			if indice == 1:
				interval = 0
				t1_anterior = t1
			else:
				interval = t1 - t1_anterior
				t1_anterior = t1
			indice = indice +1
			sec_num = int(indice)
			#aux_00 = line.split(' ')
			#sec_num = int(aux_00[0])
			indice_secuencias.append(sec_num)
			#interval = float(aux_00[1])
			#length = aux_00[2]
			#rtt = float(aux_00[3])
			#t1 = int(aux_00[4])
			#t2_t1 = int(aux_00[5])
			#t2 = t2_t1 + t1
			#t3_t2 = int(aux_00[6])
			#t3 = t3_t2 + t2
			#t4_t3 = int(aux_00[7].split('\n')[0])
			#t4 = t4_t3 + t3
			tT = t2_t1 + t4_t3					# [tT] = useg
			if length > 144:				# etiqueta, NO es el tama帽o real
				size_paquete = l_L				# [bits]
			elif length < 144:				# etiqueta, NO es el tama帽o real
				size_paquete = l_S				# [bits]
			tA_ins = size_paquete/CA		# bits/Mbps = useg
			tB_ins = size_paquete/CB		# bits/Mbps = useg
			tau = 0.5*(tT - tA_ins - tB_ins)		# [tau] = useg	eq. 17
			delay.append(tau)
			valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau]
			compara = datos_almacenados.has_key(sec_num)
			if compara == 0:
				datos_almacenados[sec_num] = valores
	tau_min = min(delay)
	tau_max = max(delay)
	tau = tau_min
	#print 'Retardo MINIMO:',tau,'useg'

	# Solo se usa para luego graficar el desfasaje entre relojes
	figura4_1 = []		# almaceno + tqA(i) + deltaPsi(i)
	figura4_2 = []		# almaceno - tqB(i) + deltaPsi(i)
	# Expresiones para calculo de los tiempos encolados
	# tqA + tqB = tT(i) - 2*tau - 2*l(i)/Csim
	# tqA + tqB = tT(i) - 2*tau - l(i)/CA - l(i)/CB		Eq. (18) TiX
	for n in indice_secuencias:
		aux_00 = datos_almacenados[n]
		t1 = aux_00[2]
		t2 = aux_00[3]
		t3 = aux_00[4]
		t4 = aux_00[5]
		tT = aux_00[6]
		tA_ins = aux_00[7]
		tB_ins = aux_00[8]
		tqA_tqB = tT - 2*tau - tA_ins - tB_ins		# [tqA_tqB] = useg	eq. 18
		#print 'tqA + tqB(',n,'):', tqA_tqB
		aux_00.append(tqA_tqB)	# valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB]
		datos_almacenados[n] = aux_00
		# 
		# Para graficar desfasaje entre relojes
		# tqA(i) + deltaPsi(i) = t2(i) - t1(i) - l(i)/CA - tau      eq. (20) TiX
		tqA_deltaPsi = t2 - t1 - tA_ins - tau
		figura4_1.append(tqA_deltaPsi)
		# - tqB(i) + deltaPsi(i) = t3(i) - t4(i) + l(i)/CB + tau    eq. (21) TiX
		tqB_deltaPsi = t3 - t4 + tB_ins + tau
		figura4_2.append(tqB_deltaPsi)

	# Busco subconjunto v
	subset_indices = []
	for n in indice_secuencias:
		aux_00 = datos_almacenados[n]
		tqA_tqB = aux_00[10]
		# Si n es impar => paquete corto
		if n % 2 != 0:
			if tqA_tqB <= lambda_S:		# eq. 18
				subset_indices.append(n)
		# Si n es par => paquete largo
		else:
			if tqA_tqB <= lambda_L:		# eq. 18
				subset_indices.append(n)

	# COMIENZO SYNC de relojes
	# deltapsi(i) = 0.5 (t2(i) - t4(i) - t1(i) + t3(i) - tqA(i) + tqB(i) - l(i)/CA + l(i)/CB )
	# deltapsi(v) = 0.5 (t2(v) - t4(v) - t1(v) + t3(v) - l(v)/CA + l(v)/CB )		Eq. (19) TiX

	# Formato de array pares_v = [v, DeltaPsi(v)]
	Dpsi_v = {}
	deltaPsi_v = []
	pares_v = []
	for m in subset_indices:
		aux_00 = datos_almacenados[m]
		t1 = aux_00[2]
		t2 = aux_00[3]
		t3 = aux_00[4]
		t4 = aux_00[5]
		tA_ins = aux_00[7]
		tB_ins = aux_00[8]
		deltaPsi = 0.5*(t2 - t4 - t1 + t3 - tA_ins + tB_ins)
		datos = (m,deltaPsi)
		pares_v.append(datos)
		# Solo para graficar
		aux_Dpsi = round(deltaPsi/1000/1000, 3)
		deltaPsi_v.append(aux_Dpsi)
		#####
		compara = Dpsi_v.has_key(m)
		if compara == 0:
			Dpsi_v[m] = datos

	# Estimaci贸n del valor inicial si v[1] != 0
	sec_inicial_i = indice_secuencias[0]
	sec_inicial_v = pares_v[0][0]
	if sec_inicial_i != sec_inicial_v:
		aux_00 = datos_almacenados[sec_inicial_i]
		t1 = aux_00[2]
		t2 = aux_00[3]
		t3 = aux_00[4]
		t4 = aux_00[5]
		tA_ins = aux_00[7]
		tB_ins = aux_00[8]
		tqA_deltaPsi = t2 - t1 - tA_ins - tau
		tqB_deltaPsi = t3 - t4 + tB_ins + tau
		Dpsi_est = tqB_deltaPsi + (tqA_deltaPsi - tqB_deltaPsi)/2
		datos = (sec_inicial_i, Dpsi_est)
		Dpsi_v[sec_inicial_i] = datos

	# Estimaci贸n del valor final
	sec_final_i = indice_secuencias[len(indice_secuencias)-1]
	sec_final_v = pares_v[len(pares_v)-1][0]
	if sec_final_i != sec_final_v:
		aux_00 = datos_almacenados[sec_final_i]
		t1 = aux_00[2]
		t2 = aux_00[3]
		t3 = aux_00[4]
		t4 = aux_00[5]
		tA_ins = aux_00[7]
		tB_ins = aux_00[8]
		tqA_deltaPsi = t2 - t1 - tA_ins - tau
		tqB_deltaPsi = t3 - t4 + tB_ins + tau
		Dpsi_est = tqB_deltaPsi + (tqA_deltaPsi - tqB_deltaPsi)/2
		datos = (sec_final_i, Dpsi_est)
		Dpsi_v[sec_final_i] = datos

	# Interpolacion
	Dpsi_i = {}
	for s in range(0,len(indice_secuencias)):
		i = indice_secuencias[s]
		# Es una secuencia con Dpsi valido ?
		compara_00 = Dpsi_v.has_key(i)
		if compara_00 != 0:		# Valida
			aux = Dpsi_v[i]
			u = aux[0]
			Du = aux[1]
			Dpsi_i[u] = aux
		else:					# No valida
			v = i+1
			for n in range(v,len(indice_secuencias)):
				compara_01 = Dpsi_v.has_key(n)
				if compara_01 != 0:		# Punto siguiente valido
					aux = Dpsi_v[n]
					v = aux[0]
					Dv = aux[1]
					break				# salgo al encontrar punto siguiente valido
			m = (Dv - Du) / (v - u)
			b = Du - m*u
			g = b + m*i
			# Condiciones que se deben cumplir para la interpolacion
			# tqA(i) = t2(i) - t1(i) - l(i)/CA - tau - DeltaPsi(i) >= 0		eq. (22) TiX
			# tqB(i) = t4(i) - t3(i) - l(i)/CB - tau + DeltaPsi(i) >= 0		eq. (23) TiX
			aux_00 = datos_almacenados[i]
			t1 = aux_00[2]
			t2 = aux_00[3]
			t3 = aux_00[4]
			t4 = aux_00[5]
			tA_ins = aux_00[7]
			tB_ins = aux_00[8]
			tqA = t2 - t1 - tA_ins - tau - g
			tqB = t4 - t3 - tB_ins - tau + g
			if tqA > 0 and tqB > 0:
				datos = (i, g)
				Dpsi_i[i] = datos
			else:
				tqA_deltaPsi = t2 - t1 - tA_ins - tau
				tqB_deltaPsi = t3 - t4 + tB_ins + tau
				# Nueva idea: comparo con los anteriores para ver de cual esta m谩s cerca
				sec_prev = indice_secuencias[s-1]
				Dpsi_a_comparar = Dpsi_i[sec_prev][1]
				if (abs(tqA_deltaPsi - Dpsi_a_comparar)) < (abs(tqB_deltaPsi - Dpsi_a_comparar)):
					Dpsi_est = tqA_deltaPsi
				else:
					Dpsi_est = tqB_deltaPsi
				datos = (i, Dpsi_est)
				u = i
				Du = Dpsi_est
				Dpsi_v[i] = datos
				Dpsi_i[i] = datos

	# Aca ya tengo Dpsi para todo i => lo agrego a la estructura de valores
	for i in Dpsi_i.keys():
		dpsi = Dpsi_i[i][1]
		aux_00 = datos_almacenados[i]
		aux_00.append(dpsi)  # valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi]
		datos_almacenados[i] = aux_00

	## GRAFICO
	## Para graficar desfasaje entre relojes, descomentar las siguientes lineas
	#x4 = []
	#y4 = []		# Dpsi(i)
	#for i in Dpsi_i.keys():
	#	aux = Dpsi_i[i]
	#	x4.append(aux[0])
	#	y = aux[1]
	#	y4.append(y)
	#
	#pylab.xlim([0,len(indice_secuencias)])
	#x1 = indice_secuencias
	#y1 = figura4_1		# + tqA(i) + deltaPsi(i)
	#y2 = figura4_2		# - tqB(i) + deltaPsi(i)
	#plt.plot(x1,y1, 'go', label='+ tqA + DPsi')
	#plt.plot(x1,y2, 'ro', label='- tqB + DPsi')
	#plt.plot(x4,y4, 'bo', label='DPsi(i)')
	#plt.ylabel('Tiempos [useg]')
	#plt.xlabel('Secuencias')
	#plt.title('Sincronizacion de relojes')
	#plt.grid(True)
	#plt.legend()
	#plt.show()

	## Para calcular y graficar Histograma para dpsi(i) - dpsi(i-1), descomentar las siguientes lineas
	#dpsi_histo = []
	#for n in range(2,len(Dpsi_i.keys())):
	#	j = int(n)
	#	i = int(n-1)
	#	if j - i == 1:
	#		compara_00 = Dpsi_i.has_key(j)
	#		compara_01 = Dpsi_i.has_key(i)
	#		if compara_00 != 0 and compara_01 != 0:
	#			dpsi_j = Dpsi_i[j][1]
	#			dpsi_i = Dpsi_i[i][1]
	#			dpsi_diff = dpsi_j - dpsi_i
	#			dpsi_histo.append(dpsi_diff)

	#delta = 250
	#dpsi_max = max(dpsi_histo)
	#dpsi_min = min(dpsi_histo)
	#bines = round((dpsi_max - dpsi_min)/delta,0)
	#paso = round((dpsi_max - dpsi_min) / bines, 2)
	#histo = scipy.histogram(dpsi_histo, bins=bines)

	#dpsi_frecuencias = histo[0]
	#dpsi_lista_frecuencias = numpy.ndarray.tolist(dpsi_frecuencias)
	#dpsi_tiempos = histo[1]
	#dpsi_lista_tiempos = numpy.ndarray.tolist(dpsi_tiempos)
	## Convierto el vector de tiempos a la misma longitud que el de frecuencias, graficando el punto de acumulacion en el punto medio del intervalo
	#size_dpsi_lista_tiempos = len(dpsi_lista_tiempos)
	#dpsi_vector_tiempos = []
	#for x in range(0,size_dpsi_lista_tiempos - 1):
	#	aux = dpsi_lista_tiempos[x]
	#	x_1 = round(aux + paso/2, 2)
	#	dpsi_vector_tiempos.append(x_1)

	## Para graficar el histograma dpsi
	#x_10 = dpsi_vector_tiempos
	#y_10 = dpsi_frecuencias
	#plt.plot(x_10,y_10, 'go')
	#plt.plot(x_10,y_10, 'g-', label='Histograma')
	#plt.ylabel('Frecuencias')
	#plt.xlabel('tiempos [us]')
	#plt.title('Histograma Dpsi(i) - Dpsi(i-1)')
	#plt.grid(True)
	#plt.legend()
	#plt.show()

	# COMIENZO CALCULOS DE tqA y tqB para todo i
	# tqA(i) = t2(i) - t1(i) - l(i)/CA - tau - DeltaPsi(i) >= 0		eq. (22) TiX
	# tqB(i) = t4(i) - t3(i) - l(i)/CB - tau + DeltaPsi(i) >= 0		eq. (23) TiX
	data_tqA = []
	data_tqB = []
	for i in indice_secuencias:
		aux_00 = datos_almacenados[i]
		t1 = aux_00[2]
		t2 = aux_00[3]
		t3 = aux_00[4]
		t4 = aux_00[5]
		tA_ins = aux_00[7]
		tB_ins = aux_00[8]
		Dpsi = Dpsi_i[i][1]
		tqA = t2 - t1 - tA_ins - tau - Dpsi
		data_tqA.append(tqA)
		aux_00.append(tqA)  # valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi, tqA]
		tqB = t4 - t3 - tB_ins - tau + Dpsi
		data_tqB.append(tqB)
		aux_00.append(tqB)  # valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi, tqA, tqB]
		datos_almacenados[i] = aux_00

	# Ajuste de los tiempos de encolado
	datos_analizar = [data_tqA, data_tqB]
	for d in range(0,len(datos_analizar)):
		data_analizar = datos_analizar[d]
		# Para saber en que caso estoy
		if d == 0:
			sentido = 'up'
		elif d == 1:
			sentido = 'down'

		delta = 250
		tq_max = max(data_analizar)
		tq_min = min(data_analizar)
		bines = round((tq_max - tq_min)/delta,0)
		paso = round((tq_max - tq_min) / bines, 2)
		histo = scipy.histogram(data_analizar, bins=bines)

		frecuencias = histo[0]
		lista_frecuencias = numpy.ndarray.tolist(frecuencias)
		tiempos = histo[1]
		lista_tiempos = numpy.ndarray.tolist(tiempos)
		# Convierto el vector de tiempos a la misma longitud que el de frecuencias, graficando el punto de acumulacion en el punto medio del intervalo
		size_lista_tiempos = len(lista_tiempos)
		vector_tiempos = []
		for x in range(0,size_lista_tiempos - 1):
			aux = lista_tiempos[x]
			x_1 = aux + paso/2
			vector_tiempos.append(x_1)

		## Para graficar el histograma
		#x_10 = vector_tiempos
		#y_10 = frecuencias
		#plt.plot(x_10,y_10, 'go')
		#plt.plot(x_10,y_10, 'g-', label='Histograma')
		#plt.ylabel('Frecuencias')
		#plt.xlabel('tiempos [us]')
		#plt.grid(True)
		#plt.title('Histograma tq'+sentido)
		#plt.legend()
		#plt.show()

		#Estimaciones
		t_first = vector_tiempos[0]
		P_max = max(frecuencias)
		indice_t_Pmax = lista_frecuencias.index(P_max)
		t_Pmax = vector_tiempos[indice_t_Pmax]
		desvio = max(delta,(t_Pmax - t_first))
		#print "t_first: "+str(t_first)
		#print "P_max: "+str(P_max)
		#print "indice_t_Pmax: "+str(indice_t_Pmax)
		#print "t_Pmax: "+str(t_Pmax)
		#print "desvio: "+str(desvio)

		# Truncamiento
		limite_truncamiento = t_Pmax + 3*desvio
		tiempos_truncados = []
		for t in vector_tiempos:
			if t <= limite_truncamiento:
				tiempos_truncados.append(t)

		# define a gaussian fitting function where
		# p[0] = amplitude
		# p[1] = mean
		# p[2] = sigma
		fitfunc = lambda p, x: p[0]*scipy.exp(-(x-p[1])**2/(2.0*p[2]**2))
		errfunc = lambda p, x, y: fitfunc(p,x)-y

		# guess some fit parameters
		p0 = scipy.c_[P_max, t_Pmax, desvio]
		errFound = False
                logger.info( "linea 1319: pmax: %s tpmax: %s, desvio: %s" % (P_max, t_Pmax, desvio) )
		if desvio > t_Pmax:
		  rollbar.report_exc_info()

                if P_max == 0 or t_Pmax == 0 or desvio == 0:
                  logger.info("I think I found a zero, pmax: %s tpmax: %s, desvio: %s" % (P_max, t_Pmax, desvio))
                  errFound = True
                  rollbar.report_exc_info()
	
		almaceno_tiempos = {}
		almaceno_cv = {}
		almaceno_estimadores = {}
		# Ajustes para diferentes series
		rango_ajuste = range(indice_t_Pmax + 1, len(tiempos_truncados))
		for el in rango_ajuste:
			xcorr = vector_tiempos[0:el+1]
			ycorr = lista_frecuencias[0:len(xcorr)]
			almaceno_tiempos[el] = xcorr
		
			# fit a gaussian
                	try: 
				p1, success = scipy.optimize.leastsq(errfunc, p0.copy()[0], args=(xcorr,ycorr))
                	except: 
				p1=p0.copy()[0]
				pass
			
			almaceno_estimadores[el] = p1
		
			amp_estimada = round(p1[0],3)
			tiempo_estimado = round(p1[1],3)
			dsv_estimado = round(p1[2],3)
		
			# Calculo coeficiente de variacion
			cv = round(dsv_estimado/tiempo_estimado, 4)
			if cv > 0:
				almaceno_cv[cv] = el
			#almaceno_cv[cv] = el

		# Ahora me quedo con el menor de los cv para calculos y graficos del ajuste
		indice_cv = almaceno_cv.keys()
		cv_min = min(indice_cv)
		elementos_tiempo = almaceno_cv[cv_min]

		p1 = almaceno_estimadores[elementos_tiempo]
		amp_estimada = round(p1[0],3)
		tiempo_estimado = round(p1[1],3)
		dsv_estimado = round(p1[2],3)
		#print "amp_estimada: "+str(amp_estimada)
		#print "tiempo_estimado: "+str(tiempo_estimado)
		#print "dsv_estimado: "+str(dsv_estimado)

		## Para graficar ajuste de los tq, descomentar las siguientes lineas
		#xcorr = almaceno_tiempos[elementos_tiempo]
		#ycorr = lista_frecuencias[0:len(xcorr)]
		#xrest = vector_tiempos[len(xcorr):len(vector_tiempos)]
		#yrest = lista_frecuencias[len(ycorr):len(lista_frecuencias)]
	#
		#arreglo = numpy.arange(t_first, limite_truncamiento, 0.01)
		#fn_est = fitfunc(p1, arreglo)
		#
		#x_test = xcorr
		#y_test = ycorr
		#plt.plot(x_test,y_test, 'go')
		#plt.plot(x_test,y_test, 'g-', label='Histograma')
		#plt.plot(xrest,yrest, 'bo')
		#plt.plot(xrest,yrest, 'b-', label='Truncamiento')
		#plt.plot(arreglo, fn_est,'r-', label='Funcion de ajuste')
		#plt.ylabel('Frecuencias')
		#plt.xlabel('tiempos [us]')
		#plt.title('Modelado de tiempos de encolado')
		#plt.grid(True)
		#plt.legend()
		#plt.show()

		# Calculo del umbral	
		umbral = tiempo_estimado + 3* dsv_estimado
		#print "umbral:"+str(umbral)
		# Calculo de utilizacion global contando cantidad de paquetes que superan el umbral
		util = 0
		for t in data_analizar:
			if t < umbral:
				util = util + 1
		util_global = 100 - 100*util/float(len(data_analizar))
		# SALIDA
		#------------------------------------------
		compara = info_necesaria.has_key(file_name)
		if compara == 0:
			info_necesaria[file_name] = [util_global]
		else:
			aux = info_necesaria[file_name]
			aux.append(util_global)
			info_necesaria[file_name] = aux
		#------------------------------------------

		## Utilizaci贸n instant谩nea
		#ventana = 60
		#salto = 1
		#x = 1
		#tiempo = []
		#label = []
		#eje_y = []
		#for s in range(1,len(indice_secuencias)-1,salto):
		#	if ventana >= len(indice_secuencias):
		#		break
		#	muestras = 0		# cantidad de muestras en la ventana de 1 minuto (puede haber secuencias que fallaron)
		#	m = 0				# cantidad de valores de tq que superaron el umbral
		#	for t in range(s,ventana+1):
		#		compara_00 = datos_almacenados.has_key(t)
		#		#print t
		#		if compara_00 != 0:
		#			muestras = muestras + 1
		#			# valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi, tqA, tqB]
		#			aux_00 = datos_almacenados[t]
		#			marcaTiempo = round(int(aux_00[2])/(1000*1000), 0)
		#			if sentido == 'up':
		#				tq = aux_00[12]		# tqA
		#			elif sentido == 'down':
		#				tq = aux_00[13]		# tqB
		#			if tq > umbral:
		#				m = m + 1
		#	if muestras != 0:
		#		y = m/float(muestras)
		#		eje_y.append(y)
		#		tiempo.append(x)
		#		label.append(marcaTiempo)
		#	x = round(x + 1/float(60), 2)
		#	ventana = ventana + salto
		#
		##busco_caso = file_name.split('/')
		##ip = busco_caso[len(busco_caso)-2]
		##nombre = busco_caso[len(busco_caso)-1].split('_')[0]
		##caso = busco_caso[len(busco_caso)-1].split('_')[1]
		##if caso == 'l.txt' and sentido == 'up':
		##	fsalida = nombre+'_l.utilizacionInstantaneaUpstream'
		##elif caso == 'l.txt' and sentido == 'down':
		##	fsalida = nombre+'_l.utilizacionInstantaneaDownstream'
		##elif caso == 'u.txt' and sentido == 'up':
		##	fsalida = nombre+'_u.utilizacionInstantaneaUpstream'
		##elif caso == 'u.txt' and sentido == 'down':
		##	fsalida = nombre+'_u.utilizacionInstantaneaDownstream'
		###path_dst = dir_base+ip+'/'
		#nombre=file_name
		#if  sentido == 'up':
		#	fsalida = nombre+'.utilizacionInstantaneaUpstream'
		#elif sentido == 'down':
		#	fsalida = nombre+'.utilizacionInstantaneaDownstream'
		#path_dst='./'
		#fsalida_abs = path_dst+fsalida
		#if os.path.isfile(fsalida_abs) == True:
		#	print 'Ya existe el archivo. Verificar si ya se hicieron los calculos.'
		##	break
		#f = open(fsalida_abs, 'a')
		#cadena = '# Utilizacion global: '+str(util_global)+' %\n'
		#f.write(cadena)
		#cadena = '# fecha [UnixTime] | tiempo [min] | utilizacion [0-1]\n'
		#f.write(cadena)
		#for n in range(0,len(tiempo)):
		#	y2 = str(label[n])
		#	x = str(tiempo[n])
		#	y1 = str(eje_y[n])
		#	cadena = y2+' '+x+' '+y1+'\n'
		#	f.write(cadena)
		#f.close()

		### Para graficar utilizacion en ventana, descomentar las siguientes lineas
		##pylab.ylim([0,1.2])
		##plt.plot(tiempo,eje_y, 'g-', label='Utilizacion')
		##plt.ylabel('% de utilizacion')
		##plt.xlabel('tiempos [min]')
		##plt.title('Utilizacion en ventana de 1 minuto')
		##plt.grid(True)
		##plt.legend()
		##plt.show()

		# Utilizaci贸n acumulada en una hora y luego ventana desplazada cada 5 minutos [depende de ventana y salto]
		# Acumulado en la primer hora y luego cada 5 minutos
		tiempo = []
		eje_y = []
		ventana_orig=1200
		salto_orig=60
		x_orig=10
		#ventana = 3600
		ventana = ventana_orig/4
		#salto = 300
		salto = salto_orig
		#x = 60				# primer valor de tiempo
		x = x_orig				# primer valor de tiempo
		label = []
		for s in range(1,len(indice_secuencias),salto):
			muestras = 0		# cantidad de muestras en la ventana de 1 minuto (puede haber secuencias que fallaron)
			m = 0				# cantidad de valores de tq que superaron el umbral
			#print "    s="+str(s)
			#print "		if ventana="+str(ventana)+"     len(indice_secuencias)="+str(len(indice_secuencias))
			if ventana > len(indice_secuencias):
				if len(tiempo) == 0:		# Hay menos muestras que las necesarias para una hora, se hace un solo calculo
					for u in range(1,len(indice_secuencias)):
						compara_00 = datos_almacenados.has_key(u)
						if compara_00 != 0:
							muestras = muestras + 1
							# valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi, tqA, tqB]
							aux_00 = datos_almacenados[u]
							marcaTiempo = round(int(aux_00[2])/(1000*1000), 0)
							if sentido == 'up':
								tq = aux_00[12]		# tqA
							elif sentido == 'down':
								tq = aux_00[13]		# tqB
							if tq > umbral:
								m = m + 1
					if muestras != 0:
						y = m/float(muestras)
						eje_y.append(y)
						tiempo.append(x)
						label.append(marcaTiempo)
				else:						# Es el ultimo intervalo de tiempos => salgo
					break
			else:
				for t in range(s,ventana+1):
					compara_00 = datos_almacenados.has_key(t)
					if compara_00 != 0:
						muestras = muestras + 1
						# valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi, tqA, tqB]
						aux_00 = datos_almacenados[t]
						marcaTiempo = round(int(aux_00[2])/(1000*1000), 0)
						if sentido == 'up':
							tq = aux_00[12]		# tqA
						elif sentido == 'down':
							tq = aux_00[13]		# tqB
						if tq > umbral:
							m = m + 1
				#print "muestras="+str(muestras)+"  m="+str(m)
				if muestras != 0:		# Solo genera salida cuando existen muestras
					y = m/float(muestras)
					eje_y.append(y)
					tiempo.append(x)
					label.append(marcaTiempo)
				x = x + 5
				ventana = ventana + salto

		#print "eje_y: "+str(eje_y)
		## Para graficar utilizacion en ventana
		#pylab.ylim([0,1.2])
		#plt.ylim([0,1.2])
		#plt.plot(tiempo,eje_y, 'r-', label='Utilizacion')
		#plt.ylabel('% de utilizacion')
		#plt.xlabel('tiempos [min]')
		#plt.title('Utilizacion en ventana de 5 minutos')
		#plt.grid(True)
		#plt.legend()
		#plt.show()

		# Par谩metro de Hurst acumulado en una hora y luego ventana desplazada cada 5 minutos [depende de 'ventana' y 'salto']
		## Acumulado en la primer hora  y luego cada 5 minutos                               [usamos los anteriores         ]
		tiempo = []
		y1_rs = []
		y2_wavelet = []
		y3_localW=[]
		y4_aggVar=[]
		#ventana = 3600
		ventana = ventana_orig
		#salto = 300
		salto = salto_orig
		#x = 60				# primer valor de tiempo
		x = x_orig				# primer valor de tiempo
		for s in range(1,len(indice_secuencias),salto):
			if ventana > len(indice_secuencias):
				if len(tiempo) == 0:		# Hay menos muestras que las necesarias para una hora, se hace un solo calculo
					for u in range(1,len(indice_secuencias)):
						compara_00 = datos_almacenados.has_key(u)
						if compara_00 != 0:
							filew=file_name+'workfile'
							f = open(filew, 'a')
							# valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi, tqA, tqB]
							aux_00 = datos_almacenados[u]
							if sentido == 'up':
								tq = aux_00[12]		# tqA
							elif sentido == 'down':
								tq = aux_00[13]		# tqB
							if tq > 0:
								aux = str(tq)
								f.write(aux+'\n')
							f.close()
					proc = subprocess.Popen(['/usr/bin/Rscript','calculoH.R'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
					stdout, stderr = proc.communicate()
					resultados = stdout
					#print " resultados: "+str(resultados)
					if len(resultados) != 0:
						aux_01 = resultados.split('RS plot H= ')
						RSa = aux_01[1].split(' \n')
						if len(RSa[0]) != 0:
					   		RS = RSa[0]
						else:
					   		RS = 0.5
						y1_rs.append(round(float(RS), 3))
						aux_02 = aux_01[1].split('Wavelet H= ')
						waveleta = aux_02[1].split(' +/-')[0]
						if len(waveleta) != 0:
					   		wavelet = float(waveleta)
						else:
					   		wavelet = 0.5
						y2_wavelet.append(round(float(wavelet), 3))
						#aux_03 = aux_01[1].split('Loc. W. H= ')
						#localW = aux_03[1].split(' \n')[0]
						#y3_localW.append(round(float(localW), 3))
						#aux_04 = aux_01[1].split('Agg var H= ')
						#aggVar = aux_04[1].split(' \n')[0]
						#y4_aggVar.append(round(float(aggVar), 3))
					else:
						y1_rs.append(0.5)
						y2_wavelet.append(0.5)

					if os.path.isfile(filew) == True:
						os.remove(filew)
					tiempo.append(x)
				else:						# Es el ultimo intervalo de tiempos => salgo
					break
			else:
				for t in range(s,ventana+1):
					compara_00 = datos_almacenados.has_key(t)
					if compara_00 != 0:
						filew=file_name+'workfile'
						f = open(filew, 'a')
						# valores = [sec_num, length, t1, t2, t3, t4, tT, tA_ins, tB_ins, tau, tqA_tqB, Dpsi, tqA, tqB]
						aux_00 = datos_almacenados[t]
						if sentido == 'up':
							tq = aux_00[12]		# tqA
						elif sentido == 'down':
							tq = aux_00[13]		# tqB
						if tq > 0:
							aux = str(tq)
							f.write(aux+'\n')
						f.close()
				proc = subprocess.Popen(['/usr/bin/Rscript','/home/pfitba/tix_production/data_processing/calculoH.R','--args',filew], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
				stdout, stderr = proc.communicate()
				resultados = stdout
				#print " resultados: "+str(resultados)
				if len(resultados) != 0:
					aux_01 = resultados.split('RS plot H= ')
					RSa = aux_01[1].split(' \n')
					if len(RSa[0]) != 0:
					   RS = RSa[0]
					else:
					   RS = 0.5
					y1_rs.append(round(float(RS), 3))
					aux_02 = aux_01[1].split('Wavelet H= ')
					waveleta = aux_02[1].split(' +/-')[0]
					if len(waveleta) != 0:
					   wavelet = float(waveleta)
					else:
					   wavelet = 0.5
					y2_wavelet.append(round(float(wavelet), 3))
					#aux_03 = aux_01[1].split('Loc. W. H= ')
					#localW = aux_03[1].split(' \n')[0]
					#y3_localW.append(round(float(localW), 3))
					#aux_04 = aux_01[1].split('Agg var H= ')
					#aggVar = aux_04[1].split(' \n')[0]
					#y4_aggVar.append(round(float(aggVar), 3))
				else:
					y1_rs.append(0.5)
					y2_wavelet.append(0.5)
				
				if os.path.isfile(filew) == True:
					os.remove(filew)
				tiempo.append(x)
				x = x + 5
				ventana = ventana + salto
		
		## Para graficar parametro de Hurst en ventana
		#plt.plot(tiempo,y1_rs, 'r-', label='RS')
		#plt.plot(tiempo,y2_wavelet, 'b-', label='Wavelet')
		#plt.ylabel('Parametro de Hurst')
		#plt.xlabel('tiempos [min]')
		#plt.title('Parametro de Hurst en ventana de 5 minutos')
		#plt.grid(True)
		#plt.legend()
		#plt.show()

		#busco_caso = file_name.split('/')
		#ip = busco_caso[len(busco_caso)-2]
		#nombre = busco_caso[len(busco_caso)-1].split('_')[0]
		#caso = busco_caso[len(busco_caso)-1].split('_')[1]
		#if caso == 'l.txt' and sentido == 'up':
		#	fsalida = nombre+'_l.utilizacionHurstUpstream'
		#elif caso == 'l.txt' and sentido == 'down':
		#	fsalida = nombre+'_l.utilizacionHurstDownstream'
		#elif caso == 'u.txt' and sentido == 'up':
		#	fsalida = nombre+'_u.utilizacionHurstUpstream'
		#elif caso == 'u.txt' and sentido == 'down':
		#	fsalida = nombre+'_u.utilizacionHurstDownstream'
		#path_dst = dir_base+ip+'/'
		##########################################################
		# Escribo archivo de salida
		##########################################################
		#nombre=file_name
		#if  sentido == 'up':
		#	fsalida = nombre+'.utilizacionHurstUpstream'
		#elif sentido == 'down':
		#	fsalida = nombre+'.utilizacionHurstDownstream'
		#path_dst='./'
		#fsalida_abs = path_dst+fsalida
		#if os.path.isfile(fsalida_abs) == True:
		#	print 'Ya existe el archivo. Verificar si ya se hicieron los calculos.'
		#	break
		#f = open(fsalida_abs, 'w')
		##cadena = '# fecha [UnixTime] | tiempo [min] | utilizacion [0-1] | H(RS) | H(Wavelet) \n'
		##cadena = '# fecha [UnixTime] | tiempo [min] | utilizacion [0-1] | H(RS) | H(Wavelet) | H(Local W) | H(Agg var)\n'
		#f.write(cadena)
		##print "len(tiempo): "+str(len(tiempo))
		##print "(tiempo): "+str(tiempo)
		#for n in range(0,len(tiempo)):
		#	x = str(tiempo[n])
		#	y1 = str(eje_y[n])
		#	y2 = str(y1_rs[n])
		#	y3 = str(y2_wavelet[n])
		#	y4 = str(label[n])
		#	#y5 = str(y3_localW[n])
		#	#y6 = str(y4_aggVar[n])
		#	cadena = y4+' '+x+' '+y1+' '+y2+' '+y3+'\n'
		#	#cadena = y4+' '+x+' '+y1+' '+y2+' '+y3+' '+y5+' '+y6+'\n'
		#	f.write(cadena)
		#f.close()
		calidad=0
		utilizacion = 0
		h_rs = 0
		h_wave = 0
		numer = 0 
		if (len(tiempo)-10<0):
			tinic=len(tiempo)-10
		else:
			tinic=0
		for n in range(tinic,len(tiempo)):
			#print "--> n:"+str(n)+"  len(eje_y):"+str(len(eje_y))+"  len(y1_rs):"+str(len(y1_rs))+"  len(y2_wavelet):"+str(len(y2_wavelet))
			if ((eje_y[n] < umbral_utiliz) and ((y1_rs[n]+y2_wavelet[n])/2 > umbral_H)):
				calidad=calidad+1
			utilizacion = utilizacion + eje_y[n]
			h_rs = h_rs + y1_rs[n]
			h_wave = h_wave + y2_wavelet[n]
			numer=numer+1
			#print sentido
			#print "calidad",calidad
			#print "utilizacion",eje_y[n]
			#print "h_rs",y1_rs[n]
			#print "h_wave",y2_wavelet[n]
			#print "numer",numer
		if  sentido == 'up':
			calidad_Up = 1-(calidad*1.0/numer)
			utiliz_Up = utilizacion/numer
			H_RS_Up = h_rs/numer
			H_Wave_Up = h_wave/numer
		elif sentido == 'down':
			calidad_Down = 1-(calidad*1.0/numer)
			utiliz_Down = utilizacion/numer
			H_RS_Down = h_rs/numer
			H_Wave_Down = h_wave/numer
	return(calidad_Up,utiliz_Up,H_RS_Up,H_Wave_Up,calidad_Down,utiliz_Down,H_RS_Down,H_Wave_Down)

def random_word(length):
   return ''.join(random.choice(string.lowercase) for i in range(length))

def analyse_data(files_to_process):
	
	logger.info("number of files: " +str(files_to_process.__len__()))
	logger.info("checkpoint 3.1")	
	# print "Processing files:", files_to_process
	leer = []
	for file_name in files_to_process:
		logger.info( file_name )
		# print "Now on",file_name
		if os.path.isfile(file_name) == True:
			f = open(file_name, 'r')
			#logger.info( f.readlines().__len__() )
			leer +=f.readlines()
			f.close()

	logger.info("checkpoint 3.2")

	umbral_utiliz=0.7 # leerlo de un archivo de configuracion
	umbral_H=0.68     # leerlo de un archivo de configuracion
	randomLogName = 'log_' + random_word(12)
	(calidad_Up,utiliz_Up,H_RS_Up,H_Wave_Up,calidad_Down,utiliz_Down,H_RS_Down,H_Wave_Down)=resultados(randomLogName,leer,umbral_utiliz,umbral_H)

	logger.info("checkpoint 3.3")

	print "calidad_Up:",calidad_Up
	print "utiliz_Up:",utiliz_Up
	print "H_RS_Up:",H_RS_Up
	print "H_Wave_Up:",H_Wave_Up
	print "calidad_Down:",calidad_Down
	print "utiliz_Down:",utiliz_Down
	print "H_RS_Down:",H_RS_Down
	print "H_Wave_Down:",H_Wave_Down
	ansDictionary = {}
	for i in ('calidad_Up', 'utiliz_Up', 'H_RS_Up', 'H_Wave_Up', 'calidad_Down', 'utiliz_Down', 'H_RS_Down', 'H_Wave_Down'):
			ansDictionary[i] = locals()[i]

	return ansDictionary

def process(ch, method, properties, body):
	analyse_data(body)
	print(" [x] Received %r" % body)


channel.basic_consume(callback, queue='process', no_ack=True)

channel.start_consuming()

if __name__ == "__main__": 

	if len(sys.argv) < 2:
     		print "usage: ./completo.py <files_to_process>\n"
     		sys.exit()

	files_to_process=[sys.argv[1]]
	analyse_data(files_to_process)
