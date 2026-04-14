Attribute VB_Name = "ControlCAN"
'Equipment type description:
'USB_ CAN: 3 ---- Single channel USB-CAN adapter
'USB_ CAN2:4 ---- Dual channel USB-CAN adapter
'------------------ Compatible with ZLG functions and data types-----------------------
'Define the data structure needed
'Data type of USB-CAN bus adapter board information.
Public Type VCI_BOARD_INFO
    hw_Version As Integer
    fw_Version As Integer
    dr_Version As Integer
    in_Version As Integer
    irq_num As Integer
    can_num As Byte
    str_Serial_Num(19) As Byte
    str_hw_Type(39) As Byte
    str_Usb_Serial(3) As Byte
End Type

'Define the data type of the CAN message frame.
Public Type VCI_ CAN_ OBJ
ID As Long
TimeStamp As Long 'Time ID
TimeFlag As Byte 'Whether to use time flag
SendType As Byte 'Send flag. Reserved, unused
RemoteFlag As Byte 'Whether it is a remote frame
ExternFlag As Byte 'Whether it is an extended frame
DataLen As Byte
data(7) As Byte
reserved(2) As Byt
End Type
'Define the data type of the CAN controller status.
Public Type VCI_CAN_STATUS
    ErrInterrupt As Byte
    regMode As Byte
    regStatus As Byte
    regALCapture As Byte
    regECCapture As Byte
    regEWLimit As Byte
    regRECounter As Byte
    regTECounter As Byte
    reserved As Long
End Type

'Define the data type of the error message.
Public Type VCI_ERR_INFO
    ErrCode As Long
    Passive_ErrData(2) As Byte
    ArLost_ErrData As Byte
End Type

'Define the data type of the initialization CAN
Public Type VCI_INIT_CONFIG
    AccCode As Long
    AccMask As Long
    InitFlag As Long
    Filter As Byte              '0,1 receives all frames. 2 standard frame filtering, 3 extended frame filtering.
    Timing0 As Byte
    Timing1 As Byte
    Mode As Byte                        'Mode: 0 means normal mode, 1 means listening only mode, and 2 means self-test mode
End Type

'Function declaration
'------------------------------ ZLG compatible functions---------------------------------
'Description of returned value:=1 Operation succeeded,=0 Operation failed,=- 1 Hardware error (if the device is not turned on)
Declare Function VCI_OpenDevice Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal reserved As Long) As Long
Declare Function VCI_CloseDevice Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long) As Long
Declare Function VCI_InitCAN Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByRef pInitConfig As VCI_INIT_CONFIG) As Long

Declare Function VCI_ReadBoardInfo Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByRef pInfo As VCI_BOARD_INFO) As Long
Declare Function VCI_ReadErrInfo Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByRef pErrInfo As VCI_ERR_INFO) As Long
Declare Function VCI_ReadCANStatus Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByRef pCANStatus As VCI_CAN_STATUS) As Long

Declare Function VCI_GetReference Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByVal reserved As Long, ByRef data As Byte) As Long
Declare Function VCI_SetReference Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByVal RefType As Long, ByRef data As Byte) As Long

Declare Function VCI_GetReceiveNum Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long) As Long
Declare Function VCI_ClearBuffer Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long) As Long

Declare Function VCI_StartCAN Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long) As Long
Declare Function VCI_ResetCAN Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long) As Long

Declare Function VCI_Receive Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByRef pReceive As VCI_CAN_OBJ, ByVal Length As Long, ByVal WaitTime As Integer) As Long
'The return value is the actual number of frames sent. If - 1 is returned, it indicates that the device is wrong
Declare Function VCI_Transmit Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByRef pSend As VCI_CAN_OBJ, ByVal Length As Long) As Long
'-------------------------------- Description of other functions and data structures---------------------------------
'Data type 1 of USB-CAN bus adapter board information, which is in VCI_ Reference in FindUsbDevice
Public Type VCI_BOARD_INFO1
    hw_Version As Integer
    fw_Version As Integer
    dr_Version As Integer
    in_Version As Integer
    irq_num As Integer
    can_num As Byte
    reserved As Byte
    str_Serial_Num(7) As Byte
    str_hw_Type(15) As Byte
    str_Usb_Serial(3, 3) As Byte
End Type


'Define general parameter types
Public Type VCI_ REF_ NORMAL
Mode As Byte
Filter As Byte
AccCode As Long 'Receive filter acceptance code
AccMask As Long 'Receive filter mask code
KBaudRate As Byte 'Baud rate index number, 0-SelfDefine, 1-5Kbps (not used), 2-18 are: 10kbps, 20kbps, 40kbps, 50kbps, 80kbps, 100kbps, 125kbps, 200kbps, 250kbps, 400kbps, 500kbps, 666kbps, 800kbps, 1000kbps, 33.33kbps, 66.66kbps, 83.33kbps
Timing0 As Byte
Timing1 As Byte
CANRX_ EN As Byte 'Reserved, unused
UARTBAUD As Byte 'Reserved, unused
End Type
'Define the baud rate setting parameter type
Public Type VCI_ BAUD_ TYPE
Baud As Long 'stores the actual baud rate
SJW As Byte 'synchronous jump width, 1-4 values
BRP As Byte 'pre frequency division value, 1-64
SAM As Byte 'sampling point, value 0=sampling once, 1=sampling three times
PHSEG2_ SEL As Byte 'Select bit of phase buffer segment 2, value 0=determined by the time of phase buffer segment 1, 1=programmable
PRSEG As Byte 'propagation time period, value 1-8
PHSEG1 As Byte 'phase buffer section 1, value 1-8
PHSEG2 As Byte 'phase buffer section 2, value 1-8
End Type
'Define the reference parameter type


Public Type VCI_REF_STRUCT
                RefNormal As VCI_REF_NORMAL
                reserved        As Byte
                BaudType As VCI_BAUD_TYPE
End Type

Declare Function VCI_GetReference2 Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByVal reserved As Long, ByRef pRefStruct As VCI_REF_STRUCT) As Long
Declare Function VCI_SetReference2 Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal CANIndex As Long, ByVal RefType As Long, ByRef data As Byte) As Long
Declare Function VCI_ResumeConfig Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long) As Long

Declare Function VCI_ConnectDevice Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long) As Long
Declare Function VCI_UsbDeviceReset Lib "ControlCAN.dll" (ByVal DevType As Long, ByVal DevIndex As Long, ByVal reserved As Long) As Long
Declare Function VCI_FindUsbDevice Lib "ControlCAN.dll" (ByRef pInfo As VCI_BOARD_INFO1) As Long

'End of file
