//-----------------------------------------------------------------------------
//   File:      Custom_Requests.c
//	 Date:		6-19-2013
//
//-----------------------------------------------------------------------------
// Copyright 2013, Cypress Semiconductor Corporation
//-----------------------------------------------------------------------------
#pragma NOIV // Do not generate interrupt vectors

#include "fx2.h"
#include "fx2regs.h"
#include "syncdly.h" // SYNCDELAY macro

extern BOOL GotSUD; // Received setup data flag
extern BOOL Sleep;
extern BOOL Rwuen;
extern BOOL Selfpwr;

BYTE Configuration;	   // Current configuration
BYTE AlternateSetting; // Alternate settings

//-----------------------------------------------------------------------------
// Constants
//-----------------------------------------------------------------------------
#define VR_RENUMERATE 0xa3 // renum
#define VR_I2C_SPEED 0xa4  // I2C bus rate, 100KHz or 400 KHz

#define VR_I2C_IO 0x22
#define RT_VENDOR_WRITE 0x40
#define RT_VENDOR_READ 0xc0

#define VR_GPIO 0x23
#define VR_GPIO_OE 0x24
#define VR_GPIO_IO 0x25

#define EP0BUFF_SIZE 0x40
// #define TNG 0x01

//-----------------------------------------------------------------------------
// Global Variables
//-----------------------------------------------------------------------------
BOOL as_400KHz;

//-----------------------------------------------------------------------------
// Prototypes
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// Task Dispatcher hooks
//	The following hooks are called by the task dispatcher.
//-----------------------------------------------------------------------------

void TD_Init(void) // Called once at startup
{
	// BYTE dum;
	Rwuen = TRUE; // Enable remote-wakeup

	// Indicate if it is a dual byte address part
	// DB_Addr = 1; // hard-wire for large EEPROM

	// set PA0 for output
	PORTACFG = 0x00; // port function

	// default to I2C bus freq = 100 KHz
	I2CTL &= ~bm400KHZ; // 0: 100 KHz
	as_400KHz = FALSE;
	EZUSB_InitI2C(); // Initialize I2C bus
}

void TD_Poll(void) // Called repeatedly while the device is idle
{
}

BOOL TD_Suspend(void) // Called before the device goes into suspend mode
{
	return (TRUE);
}

BOOL TD_Resume(void) // Called after the device resumes
{
	return (TRUE);
}

//-----------------------------------------------------------------------------
// Device Request hooks
//   The following hooks are called by the end point 0 device request parser.
//-----------------------------------------------------------------------------

BOOL DR_GetDescriptor(void)
{
	return (TRUE);
}

BOOL DR_SetConfiguration(void) // Called when a Set Configuration command is received
{
	Configuration = SETUPDAT[2];
	return (TRUE); // Handled by user code
}

BOOL DR_GetConfiguration(void) // Called when a Get Configuration command is received
{
	EP0BUF[0] = Configuration;
	EP0BCH = 0;
	EP0BCL = 1;
	return (TRUE); // Handled by user code
}

BOOL DR_SetInterface(void) // Called when a Set Interface command is received
{
	AlternateSetting = SETUPDAT[2];
	return (TRUE); // Handled by user code
}

BOOL DR_GetInterface(void) // Called when a Set Interface command is received
{
	EP0BUF[0] = AlternateSetting;
	EP0BCH = 0;
	EP0BCL = 1;
	return (TRUE); // Handled by user code
}

BOOL DR_GetStatus(void)
{
	return (TRUE);
}

BOOL DR_ClearFeature(void)
{
	return (TRUE);
}

BOOL DR_SetFeature(void)
{
	return (TRUE);
}

BOOL DR_VendorCmnd(void)
{
	WORD len;
	BYTE I2C_Addr;
	BYTE bc, i, type, port;

	switch (SETUPDAT[1])
	{
	// Set the I2C bus rate. Install a jumper plug between P8-37 and P8-39 to see the green LED
	case VR_I2C_SPEED:
		if (SETUPDAT[0] == RT_VENDOR_WRITE)
		{
			if ((BOOL)SETUPDAT[2] == TRUE)
			{
				I2CTL |= bm400KHZ; // nonzero: 400 KHz
				as_400KHz = TRUE;
			}
			else
			{
				I2CTL &= ~bm400KHZ; // 0: 100 KHz
				as_400KHz = FALSE;
			}
		}
		else if (SETUPDAT[0] == RT_VENDOR_READ)
		{
			while (EP0CS & bmEPBUSY)
				;

			EP0BUF[0] = as_400KHz;

			EP0BCH = 0;
			SYNCDELAY;
			EP0BCL = 1; // Arm endpoint with # bytes to transfer
			SYNCDELAY;
		}

		break;

	case VR_RENUMERATE:
		if (SETUPDAT[0] == RT_VENDOR_WRITE)
		{
			EP0CS |= bmHSNAK; // Acknowledge handshake phase of device request
			EZUSB_Delay(1000);
			EZUSB_Discon(TRUE); // renumerate until setup received
		}

		break;

	case VR_I2C_IO:

		I2C_Addr = SETUPDAT[2];
		len = SETUPDAT[7] << 8 | SETUPDAT[6];

		if (SETUPDAT[0] == RT_VENDOR_READ)
		{
			while (len)
			{
				while (EP0CS & bmEPBUSY)
					;

				if (len < EP0BUFF_SIZE)
					bc = len;
				else
					bc = EP0BUFF_SIZE;

				for (i = 0; i < EP0BUFF_SIZE; i++) // clear buffer
					EP0BUF[i] = 0x00;

				EZUSB_ReadI2C(I2C_Addr, bc, EP0BUF); // I2C Read

				EP0BCH = 0;
				SYNCDELAY;
				EP0BCL = bc; // Arm endpoint with # bytes to transfer
				SYNCDELAY;

				len -= bc;
			}
		}
		else if (SETUPDAT[0] == RT_VENDOR_WRITE)
		{
			while (len)
			{
				// Arm endpoint - do it here to clear (after sud avail)
				EP0BCH = 0;
				SYNCDELAY;
				EP0BCL = 0; // Clear bytecount to allow new data in; also stops NAKing
				SYNCDELAY;

				while (EP0CS & bmEPBUSY)
					;

				bc = EP0BCL;						  // Get the new bytecount
				EZUSB_WriteI2C(I2C_Addr, bc, EP0BUF); //I2C Write

				len -= bc;
			}
		}

		break;

	case VR_GPIO:

		type = SETUPDAT[2];
		port = SETUPDAT[4];

		if (SETUPDAT[0] == RT_VENDOR_READ)
		{
			while (EP0CS & bmEPBUSY)
				;

			if (type == VR_GPIO_OE)
			{
				if (port == 0)
					EP0BUF[0] = OEA;
				else if (port == 1)
					EP0BUF[0] = OEB;
			}
			else if (type == VR_GPIO_IO)
			{
				if (port == 0)
					EP0BUF[0] = IOA;
				else if (port == 1)
					EP0BUF[0] = IOB;
			}

			EP0BCH = 0;
			SYNCDELAY;
			EP0BCL = 1; // Arm endpoint with # bytes to transfer
			SYNCDELAY;
		}
		else if (SETUPDAT[0] == RT_VENDOR_WRITE)
		{
			// Arm endpoint - do it here to clear (after sud avail)
			EP0BCH = 0;
			SYNCDELAY;
			EP0BCL = 0; // Clear bytecount to allow new data in; also stops NAKing
			SYNCDELAY;

			while (EP0CS & bmEPBUSY)
				;

			if (type == VR_GPIO_OE)
			{
				if (port == 0)
					OEA = EP0BUF[0];
				else if (port == 1)
					OEB = EP0BUF[0];
			}
			else if (type == VR_GPIO_IO)
			{

				if (port == 0)
					IOA = IOA & ~OEA | (EP0BUF[0] & OEA);
				else if (port == 1)
					IOB = IOB & ~OEB | (EP0BUF[0] & OEB);
			}
		}

		break;
	}
	return (FALSE); // no error; command handled OK
}

//-----------------------------------------------------------------------------
// USB Interrupt Handlers
//   The following functions are called by the USB interrupt jump table.
//-----------------------------------------------------------------------------

// Setup Data Available Interrupt Handler
void ISR_Sudav(void) interrupt 0
{
	GotSUD = TRUE; // Set flag
	EZUSB_IRQ_CLEAR();
	USBIRQ = bmSUDAV; // Clear SUDAV IRQ
}

// Setup Token Interrupt Handler
void ISR_Sutok(void) interrupt 0
{
	EZUSB_IRQ_CLEAR();
	USBIRQ = bmSUTOK; // Clear SUTOK IRQ
}

void ISR_Sof(void) interrupt 0
{
	EZUSB_IRQ_CLEAR();
	USBIRQ = bmSOF; // Clear SOF IRQ
}

void ISR_Ures(void) interrupt 0
{
	// whenever we get a USB reset, we should revert to full speed mode
	pConfigDscr = pFullSpeedConfigDscr;
	((CONFIGDSCR xdata *)pConfigDscr)->type = CONFIG_DSCR;
	pOtherConfigDscr = pHighSpeedConfigDscr;
	((CONFIGDSCR xdata *)pOtherConfigDscr)->type = OTHERSPEED_DSCR;

	EZUSB_IRQ_CLEAR();
	USBIRQ = bmURES; // Clear URES IRQ
}

void ISR_Susp(void) interrupt 0
{
	Sleep = TRUE;
	EZUSB_IRQ_CLEAR();
	USBIRQ = bmSUSP;
}

void ISR_Highspeed(void) interrupt 0
{
	if (EZUSB_HIGHSPEED())
	{
		pConfigDscr = pHighSpeedConfigDscr;
		((CONFIGDSCR xdata *)pConfigDscr)->type = CONFIG_DSCR;
		pOtherConfigDscr = pFullSpeedConfigDscr;
		((CONFIGDSCR xdata *)pOtherConfigDscr)->type = OTHERSPEED_DSCR;
	}

	EZUSB_IRQ_CLEAR();
	USBIRQ = bmHSGRANT;
}
void ISR_Ep0ack(void) interrupt 0
{
}
void ISR_Stub(void) interrupt 0
{
}
void ISR_Ep0in(void) interrupt 0
{
}
void ISR_Ep0out(void) interrupt 0
{
}
void ISR_Ep1in(void) interrupt 0
{
}
void ISR_Ep1out(void) interrupt 0
{
}
void ISR_Ep2inout(void) interrupt 0
{
}
void ISR_Ep4inout(void) interrupt 0
{
}
void ISR_Ep6inout(void) interrupt 0
{
}
void ISR_Ep8inout(void) interrupt 0
{
}
void ISR_Ibn(void) interrupt 0
{
}
void ISR_Ep0pingnak(void) interrupt 0
{
}
void ISR_Ep1pingnak(void) interrupt 0
{
}
void ISR_Ep2pingnak(void) interrupt 0
{
}
void ISR_Ep4pingnak(void) interrupt 0
{
}
void ISR_Ep6pingnak(void) interrupt 0
{
}
void ISR_Ep8pingnak(void) interrupt 0
{
}
void ISR_Errorlimit(void) interrupt 0
{
}
void ISR_Ep2piderror(void) interrupt 0
{
}
void ISR_Ep4piderror(void) interrupt 0
{
}
void ISR_Ep6piderror(void) interrupt 0
{
}
void ISR_Ep8piderror(void) interrupt 0
{
}
void ISR_Ep2pflag(void) interrupt 0
{
}
void ISR_Ep4pflag(void) interrupt 0
{
}
void ISR_Ep6pflag(void) interrupt 0
{
}
void ISR_Ep8pflag(void) interrupt 0
{
}
void ISR_Ep2eflag(void) interrupt 0
{
}
void ISR_Ep4eflag(void) interrupt 0
{
}
void ISR_Ep6eflag(void) interrupt 0
{
}
void ISR_Ep8eflag(void) interrupt 0
{
}
void ISR_Ep2fflag(void) interrupt 0
{
}
void ISR_Ep4fflag(void) interrupt 0
{
}
void ISR_Ep6fflag(void) interrupt 0
{
}
void ISR_Ep8fflag(void) interrupt 0
{
}
void ISR_GpifComplete(void) interrupt 0
{
}
void ISR_GpifWaveform(void) interrupt 0
{
}
