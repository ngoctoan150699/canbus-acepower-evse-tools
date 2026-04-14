<?xml version='1.0' encoding='UTF-8'?>
<Project Type="Project" LVVersion="11008008">
	<Item Name="my computer" Type="My Computer">
		<Property Name="NI.SortType" Type="Int">3</Property>
		<Property Name="server.app.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.control.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.tcp.enabled" Type="Bool">false</Property>
		<Property Name="server.tcp.port" Type="Int">0</Property>
		<Property Name="server.tcp.serviceName" Type="Str">my computer/VI服务器</Property>
		<Property Name="server.tcp.serviceName.default" Type="Str">my computer/VI服务器</Property>
		<Property Name="server.vi.callsEnabled" Type="Bool">true</Property>
		<Property Name="server.vi.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="specify.custom.address" Type="Bool">false</Property>
		<Item Name="Demo" Type="Folder">
			<Item Name="Demo_Main.vi" Type="VI" URL="../Demo/Demo_Main.vi"/>
			<Item Name="Demo_MakeData.vi" Type="VI" URL="../Demo/Demo_MakeData.vi"/>
			<Item Name="Demo_MakeDispBuff.vi" Type="VI" URL="../Demo/Demo_MakeDispBuff.vi"/>
			<Item Name="Demo_UpdateList.vi" Type="VI" URL="../Demo/Demo_UpdateList.vi"/>
			<Item Name="Demo_GetT0T1.vi" Type="VI" URL="../Demo/Demo_GetT0T1.vi"/>
		</Item>
		<Item Name="ControlCAN.lvlib" Type="Library" URL="../ControlCAN/ControlCAN.lvlib"/>
		<Item Name="依赖关系" Type="Dependencies">
			<Item Name="vi.lib" Type="Folder">
				<Item Name="Clear Errors.vi" Type="VI" URL="/&lt;vilib&gt;/Utility/error.llb/Clear Errors.vi"/>
				<Item Name="List Directory and LLBs.vi" Type="VI" URL="/&lt;vilib&gt;/Utility/libraryn.llb/List Directory and LLBs.vi"/>
				<Item Name="Recursive File List.vi" Type="VI" URL="/&lt;vilib&gt;/Utility/libraryn.llb/Recursive File List.vi"/>
				<Item Name="Trim Whitespace.vi" Type="VI" URL="/&lt;vilib&gt;/Utility/error.llb/Trim Whitespace.vi"/>
				<Item Name="whitespace.ctl" Type="VI" URL="/&lt;vilib&gt;/Utility/error.llb/whitespace.ctl"/>
			</Item>
		</Item>
		<Item Name="程序生成规范" Type="Build">
			<Item Name="USB_CAN Example1" Type="EXE">
				<Property Name="App_INI_aliasGUID" Type="Str">{C0CC83B7-1B72-4C69-A633-74B465F3A9FC}</Property>
				<Property Name="App_INI_GUID" Type="Str">{8DDD8E83-4910-4A25-906C-A9F229F191CE}</Property>
				<Property Name="Bld_buildCacheID" Type="Str">{D8A7B823-0CA9-4267-9493-098D9236D7BD}</Property>
				<Property Name="Bld_buildSpecName" Type="Str">USB_CAN Example1</Property>
				<Property Name="Bld_defaultLanguage" Type="Str">ChineseS</Property>
				<Property Name="Bld_excludeLibraryItems" Type="Bool">true</Property>
				<Property Name="Bld_excludePolymorphicVIs" Type="Bool">true</Property>
				<Property Name="Bld_localDestDir" Type="Path">../builds/NI_AB_PROJECTNAME/USB_CAN Example1</Property>
				<Property Name="Bld_localDestDirType" Type="Str">relativeToCommon</Property>
				<Property Name="Bld_modifyLibraryFile" Type="Bool">true</Property>
				<Property Name="Bld_previewCacheID" Type="Str">{C64DB801-15F3-4D9D-8DC1-755D7EDEC7D1}</Property>
				<Property Name="Bld_targetDestDir" Type="Path"></Property>
				<Property Name="Destination[0].destName" Type="Str">USB_CAN Example.exe</Property>
				<Property Name="Destination[0].path" Type="Path">../builds/NI_AB_PROJECTNAME/USB_CAN Example1/USB_CAN Example.exe</Property>
				<Property Name="Destination[0].type" Type="Str">App</Property>
				<Property Name="Destination[1].destName" Type="Str">Support directory</Property>
				<Property Name="Destination[1].path" Type="Path">../builds/NI_AB_PROJECTNAME/USB_CAN Example1/data</Property>
				<Property Name="DestinationCount" Type="Int">2</Property>
				<Property Name="Exe_actXinfo_enumCLSID[0]" Type="Str">{A84BB62D-2E24-4003-A9B1-C214732013CB}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[1]" Type="Str">{F31B4A0A-C0EE-4B72-A961-A2E8E2E70A81}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[10]" Type="Str">{709CCC4A-8D8D-4F30-B971-EB583B096893}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[11]" Type="Str">{F97D3C75-513F-480F-B869-54C386B4B395}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[12]" Type="Str">{83579988-AD8A-463F-B765-28D88CFC20E4}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[13]" Type="Str">{F94FDAD8-B10F-4A89-B348-7855E240CBBE}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[14]" Type="Str">{B3EA4368-D57A-404C-9C19-C2084FE79955}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[15]" Type="Str">{19881962-B051-484C-81D8-A5EAD2DC1EA4}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[16]" Type="Str">{A00B946F-B1B3-45DD-B85B-6E6C0A32B894}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[2]" Type="Str">{0A318272-C0CC-4347-A824-FF91142CFEF4}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[3]" Type="Str">{B3C6E69A-112F-4AEE-92BA-A2F9878E803D}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[4]" Type="Str">{65DB3105-8682-4E6A-B49A-3DBD8E18181B}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[5]" Type="Str">{86F6DE5A-27F5-42A4-A0D6-E0A4F6A21726}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[6]" Type="Str">{61445F6E-5DB1-411B-9AF8-29E0969B3F53}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[7]" Type="Str">{3F4A39DA-616B-493A-BD3B-75F8069F6305}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[8]" Type="Str">{C11DB467-ED21-4C10-8146-3DCC1742BF79}</Property>
				<Property Name="Exe_actXinfo_enumCLSID[9]" Type="Str">{55319678-2061-4EC4-9E05-1B06D7BDE1E8}</Property>
				<Property Name="Exe_actXinfo_enumCLSIDsCount" Type="Int">17</Property>
				<Property Name="Exe_actXinfo_majorVersion" Type="Int">5</Property>
				<Property Name="Exe_actXinfo_minorVersion" Type="Int">5</Property>
				<Property Name="Exe_actXinfo_objCLSID[0]" Type="Str">{3A5DCAC8-39E8-4872-B889-4FE00803EA53}</Property>
				<Property Name="Exe_actXinfo_objCLSID[1]" Type="Str">{EB8A6753-ABDE-4C3A-8857-33963C3EF2CB}</Property>
				<Property Name="Exe_actXinfo_objCLSID[2]" Type="Str">{046AD256-5B8D-4510-882B-724E80DAE72F}</Property>
				<Property Name="Exe_actXinfo_objCLSID[3]" Type="Str">{2E544A10-C2AD-4445-97EF-3D8C2042C8F2}</Property>
				<Property Name="Exe_actXinfo_objCLSID[4]" Type="Str">{51207E43-2096-4583-B2F8-1A1DC3F61132}</Property>
				<Property Name="Exe_actXinfo_objCLSID[5]" Type="Str">{D9F42E7D-9023-4CF1-B83D-D40003088953}</Property>
				<Property Name="Exe_actXinfo_objCLSIDsCount" Type="Int">6</Property>
				<Property Name="Exe_actXinfo_progIDPrefix" Type="Str">USBCANExample</Property>
				<Property Name="Exe_actXServerName" Type="Str">USBCANExample</Property>
				<Property Name="Exe_actXServerNameGUID" Type="Str"></Property>
				<Property Name="Source[0].itemID" Type="Str">{9FB01A42-DEFB-4D88-986F-E1B77133EEA4}</Property>
				<Property Name="Source[0].type" Type="Str">Container</Property>
				<Property Name="Source[1].destinationIndex" Type="Int">0</Property>
				<Property Name="Source[1].itemID" Type="Ref">/my computer/Demo/Demo_Main.vi</Property>
				<Property Name="Source[1].sourceInclusion" Type="Str">TopLevel</Property>
				<Property Name="Source[1].type" Type="Str">VI</Property>
				<Property Name="Source[2].destinationIndex" Type="Int">0</Property>
				<Property Name="Source[2].itemID" Type="Ref">/my computer/ControlCAN.lvlib</Property>
				<Property Name="Source[2].Library.allowMissingMembers" Type="Bool">true</Property>
				<Property Name="Source[2].sourceInclusion" Type="Str">Include</Property>
				<Property Name="Source[2].type" Type="Str">Library</Property>
				<Property Name="Source[3].destinationIndex" Type="Int">0</Property>
				<Property Name="Source[3].itemID" Type="Ref">/my computer/Demo/Demo_MakeData.vi</Property>
				<Property Name="Source[3].sourceInclusion" Type="Str">Include</Property>
				<Property Name="Source[3].type" Type="Str">VI</Property>
				<Property Name="Source[4].destinationIndex" Type="Int">0</Property>
				<Property Name="Source[4].itemID" Type="Ref">/my computer/Demo/Demo_MakeDispBuff.vi</Property>
				<Property Name="Source[4].sourceInclusion" Type="Str">Include</Property>
				<Property Name="Source[4].type" Type="Str">VI</Property>
				<Property Name="Source[5].destinationIndex" Type="Int">0</Property>
				<Property Name="Source[5].itemID" Type="Ref">/my computer/Demo/Demo_UpdateList.vi</Property>
				<Property Name="Source[5].sourceInclusion" Type="Str">Include</Property>
				<Property Name="Source[5].type" Type="Str">VI</Property>
				<Property Name="Source[6].destinationIndex" Type="Int">0</Property>
				<Property Name="Source[6].itemID" Type="Ref">/my computer/Demo/Demo_GetT0T1.vi</Property>
				<Property Name="Source[6].sourceInclusion" Type="Str">Include</Property>
				<Property Name="Source[6].type" Type="Str">VI</Property>
				<Property Name="SourceCount" Type="Int">7</Property>
				<Property Name="TgtF_fileDescription" Type="Str">USB_CAN Example1</Property>
				<Property Name="TgtF_fileVersion.major" Type="Int">1</Property>
				<Property Name="TgtF_internalName" Type="Str">USB_CAN Example1</Property>
				<Property Name="TgtF_legalCopyright" Type="Str">版权 2015 </Property>
				<Property Name="TgtF_productName" Type="Str">USB_CAN Example1</Property>
				<Property Name="TgtF_targetfileGUID" Type="Str">{20F647A3-C102-4DCC-A2A7-BFEAA776242D}</Property>
				<Property Name="TgtF_targetfileName" Type="Str">USB_CAN Example.exe</Property>
			</Item>
		</Item>
	</Item>
</Project>
