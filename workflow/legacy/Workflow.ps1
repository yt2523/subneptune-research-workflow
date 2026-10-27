param(
 [ValidateSet('New','Code','Review','Status','Report','Pause','Approve','Checkpoint')][string]$Action='Status',
 [string]$Run,[string]$Task,[string]$Repo,[string]$Scope
)
$ErrorActionPreference='Stop'
$env:TEMP='D:\Codex\tmp';$env:TMP=$env:TEMP
$py='C:\Users\PC\AppData\Local\Programs\Python\Python312\python.exe'
$root=$PSScriptRoot
if($Action -eq 'New'){
 $arguments=@("$root\workflow.py",'new')
 if($Task){$arguments+=@('--file',$Task)}
 if($Repo){$arguments+=@('--repo',$Repo)}
 if($Scope){$arguments+=@('--scope',$Scope)}
}elseif($Action -in @('Code','Review')){
 if(-not $Run){throw '-Run is required'}
 $role=if($Action -eq 'Code'){'coder'}else{'reviewer'}
 $arguments=@("$root\agents.py",$role,'--run',$Run)
 if($Task){$arguments+=@('--task',$Task)}
}else{
 if(-not $Run){throw '-Run is required'}
 $arguments=@("$root\workflow.py",$Action.ToLower(),'--run',$Run)
}
& $py @arguments
if($LASTEXITCODE -ne 0){throw "Workflow stopped (exit $LASTEXITCODE). Inspect state.json and event logs; do not blindly retry model calls."}
