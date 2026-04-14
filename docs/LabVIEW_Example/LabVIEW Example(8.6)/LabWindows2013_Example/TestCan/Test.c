#include<windows.h>
#include<windef.h>
#include <userint.h>
#include<stdio.h>
#include"ControlCAN.h"  

VCI_CAN_OBJ sendbuf;
VCI_CAN_OBJ pCanObj;

int  main()
{
  VCI_INIT_CONFIG InitInfo; 
  int flag =0;
   printf("============================================\r\n"); 
   printf("======== USB CAN Device test demo ==========\r\n"); 
   printf("== 创芯光电科技有限公司 copy right 2014 ====\r\n");
   printf("============================================\r\n\r\n");
   printf(">>>Step1:Open device:");
  //打开CAN
    if(VCI_OpenDevice(VCI_USBCAN2,0,0)!=1)
	{
		printf("  Faild!\r\n");
		goto ERR;
	}
	else
	{
		printf("Success!\r\n");
	}
	    
   	//初始化CAN  
	InitInfo.Timing0=0x00;
	InitInfo.Timing1=0x14;  //初始化CAN的波特率为1M
	InitInfo.Filter=1;		 
	InitInfo.AccCode=0x8000000;
	InitInfo.AccMask=0xFFFFFFFF;
	InitInfo.Mode=2;    //
	printf("\r\n>>>Step2:InitCAN and StartCAN(selftest mode)\r\n");
	printf("     Ch0:InitCAN:    ");
    //初始化通道0                                                        
	if(VCI_InitCAN(VCI_USBCAN2,0, 0,&InitInfo)!=1)	//can-0                  
	{      
		printf("  Failed!\r\n");                          
	                                                                     
	}  
	else
	{
		printf("Success!\r\n"); 
		printf("         StartCAN:   ");  
		if(VCI_StartCAN(VCI_USBCAN2,0,0) != 1)
			printf("  Failed!\r\n");
		else
			printf("Success!\r\n");
	}
	printf("     Ch1:InitCAN:    ");
    //初始化通道1                                                       
	if(VCI_InitCAN(VCI_USBCAN2,0, 1,&InitInfo)!=1)	//can-1                  
	{      
		printf("  Failed!\r\n");                          
	                                                                     
	}  
	else
	{
		printf("Success!\r\n"); 
		printf("         StartCAN:   ");  
		if(VCI_StartCAN(VCI_USBCAN2,0,1) != 1)
			printf("  Failed!\r\n");
		else
			printf("Success!\r\n");
	}
	printf("\r\n>>>Step3:Send and Receive test\r\n");       
	sendbuf.ID=0x18ff0080;
	sendbuf.RemoteFlag=0;  //数据帧
	sendbuf.ExternFlag=1;   //接收扩展帧
	sendbuf.DataLen = 8;
	 for(BYTE i=0;i<8;i++)
	 sendbuf.Data[i]=i;
	 
	printf("     Ch0:Send:       ");
   	flag=VCI_Transmit(VCI_USBCAN2,0,0,&sendbuf,1);//CAN message send
	if(flag<1)
	{
		if(flag==-1)
			printf("  Failed, return value = -1, the device is invalid!\r\n"); 
		else if(flag==0)
			printf("  Failed!\r\n");

	}
	else
		printf("Success!\r\n");   	
	printf("         Receive:    ");
    flag=VCI_Receive(VCI_USBCAN2,0,0,&pCanObj,1,100);
	if(flag<1)
	{
		if(flag==-1)
			printf("  Failed, return value = -1, the device is invalid!\r\n"); 
		else if(flag==0)
			printf("  Failed!\r\n"); 

	}
	else   
		printf("Success!\r\n");
	
	
	printf("     Ch1:Send:       ");
   	flag=VCI_Transmit(VCI_USBCAN2,0,1,&sendbuf,1);//CAN message send
	if(flag<1)
	{
		if(flag==-1)
			printf("  Failed, return value = -1, the device is invalid!\r\n"); 
		else if(flag==0)
			printf("  Failed!\r\n");

	}
	else
		printf("Success!\r\n");   	
	printf("         Receive:    ");
    flag=VCI_Receive(VCI_USBCAN2,0,1,&pCanObj,1,100);
	if(flag<1)
	{
		if(flag==-1)
			printf("  Failed, return value = -1, the device is invalid!\r\n"); 
		else if(flag==0)
			printf("  Failed!\r\n"); 

	}
	else   
		printf("Success!\r\n");
	
	
	printf("\r\n>>>Step4:CloseDevice:");
	
	if(VCI_CloseDevice(VCI_USBCAN2,0) != 1)
		printf("  Failed!\r\n");
	else
		printf("Success!\r\n");
	printf("============================================\r\n");
	printf("\r\nTest over,press [return] key to exit!\r\n"); 
	goto END;

ERR:
	printf("============================================\r\n");
	printf("An error happend,test failed,press [return] key to exit!\r\n");
	goto END;
	
END:
	scanf("1");
}						
