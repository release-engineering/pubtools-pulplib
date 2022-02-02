Search.setIndex({docnames:["api/client","api/containers","api/files","api/maintenance","api/pulpcore","api/searching","api/testing","api/yum","index","logging","schema"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.intersphinx":1,"sphinx.ext.viewcode":1,sphinx:56},filenames:["api/client.rst","api/containers.rst","api/files.rst","api/maintenance.rst","api/pulpcore.rst","api/searching.rst","api/testing.rst","api/yum.rst","index.rst","logging.rst","schema.rst"],objects:{"pubtools.pulplib":[[0,0,1,"","Client"],[1,0,1,"","ContainerImageRepository"],[1,0,1,"","ContainerSyncOptions"],[5,0,1,"","Criteria"],[0,0,1,"","DetachedException"],[4,0,1,"","Distributor"],[7,0,1,"","ErratumModule"],[7,0,1,"","ErratumPackage"],[7,0,1,"","ErratumPackageCollection"],[7,0,1,"","ErratumReference"],[7,0,1,"","ErratumUnit"],[6,0,1,"","FakeController"],[2,0,1,"","FileRepository"],[2,0,1,"","FileSyncOptions"],[2,0,1,"","FileUnit"],[0,0,1,"","InvalidDataException"],[3,0,1,"","MaintenanceEntry"],[3,0,1,"","MaintenanceReport"],[5,0,1,"","Matcher"],[7,0,1,"","ModulemdDefaultsUnit"],[7,0,1,"","ModulemdDependency"],[7,0,1,"","ModulemdUnit"],[5,0,1,"","Page"],[4,0,1,"","PublishOptions"],[0,0,1,"","PulpException"],[4,0,1,"","PulpObject"],[4,0,1,"","Repository"],[7,0,1,"","RpmDependency"],[7,0,1,"","RpmUnit"],[4,0,1,"","SyncOptions"],[4,0,1,"","Task"],[0,0,1,"","TaskFailedException"],[4,0,1,"","Unit"],[7,0,1,"","YumRepoMetadataFileUnit"],[7,0,1,"","YumRepository"],[7,0,1,"","YumSyncOptions"]],"pubtools.pulplib.Client":[[0,1,1,"","copy_content"],[0,1,1,"","get_content_type_ids"],[0,1,1,"","get_maintenance_report"],[0,1,1,"","get_repository"],[0,1,1,"","search_content"],[0,1,1,"","search_distributor"],[0,1,1,"","search_repository"],[0,1,1,"","search_task"],[0,1,1,"","set_maintenance"],[0,1,1,"","update_content"]],"pubtools.pulplib.ContainerImageRepository":[[1,2,1,"","registry_id"]],"pubtools.pulplib.ContainerSyncOptions":[[1,2,1,"","tags"],[1,2,1,"","upstream_name"]],"pubtools.pulplib.Criteria":[[5,1,1,"","and_"],[5,1,1,"","or_"],[5,1,1,"","true"],[5,1,1,"","with_field"],[5,1,1,"","with_id"],[5,1,1,"","with_unit_type"]],"pubtools.pulplib.Distributor":[[4,1,1,"","delete"],[4,2,1,"","id"],[4,2,1,"","is_rsync"],[4,2,1,"","last_publish"],[4,2,1,"","relative_url"],[4,2,1,"","repo_id"],[4,2,1,"","type_id"]],"pubtools.pulplib.ErratumModule":[[7,2,1,"","arch"],[7,2,1,"","context"],[7,2,1,"","name"],[7,2,1,"","stream"],[7,2,1,"","version"]],"pubtools.pulplib.ErratumPackage":[[7,2,1,"","arch"],[7,2,1,"","epoch"],[7,2,1,"","filename"],[7,2,1,"","md5sum"],[7,2,1,"","name"],[7,2,1,"","reboot_suggested"],[7,2,1,"","release"],[7,2,1,"","sha1sum"],[7,2,1,"","sha256sum"],[7,2,1,"","src"],[7,2,1,"","version"]],"pubtools.pulplib.ErratumPackageCollection":[[7,2,1,"","module"],[7,2,1,"","name"],[7,2,1,"","packages"],[7,2,1,"","short"]],"pubtools.pulplib.ErratumReference":[[7,2,1,"","href"],[7,2,1,"","id"],[7,2,1,"","title"],[7,2,1,"","type"]],"pubtools.pulplib.ErratumUnit":[[7,2,1,"","content_types"],[7,2,1,"","description"],[7,2,1,"","from_"],[7,2,1,"","id"],[7,2,1,"","issued"],[7,2,1,"","pkglist"],[7,2,1,"","pushcount"],[7,2,1,"","reboot_suggested"],[7,2,1,"","references"],[7,2,1,"","release"],[7,2,1,"","repository_memberships"],[7,2,1,"","rights"],[7,2,1,"","severity"],[7,2,1,"","solution"],[7,2,1,"","status"],[7,2,1,"","summary"],[7,2,1,"","title"],[7,2,1,"","type"],[7,2,1,"","unit_id"],[7,2,1,"","updated"],[7,2,1,"","version"]],"pubtools.pulplib.FakeController":[[6,2,1,"","client"],[6,3,1,"","content_type_ids"],[6,1,1,"","insert_repository"],[6,1,1,"","insert_task"],[6,1,1,"","insert_units"],[6,3,1,"","publish_history"],[6,3,1,"","repositories"],[6,1,1,"","set_content_type_ids"],[6,3,1,"","sync_history"],[6,3,1,"","tasks"]],"pubtools.pulplib.FileRepository":[[2,1,1,"","upload_file"]],"pubtools.pulplib.FileSyncOptions":[[2,2,1,"","remove_missing"]],"pubtools.pulplib.FileUnit":[[2,2,1,"","cdn_path"],[2,2,1,"","cdn_published"],[2,2,1,"","description"],[2,2,1,"","display_order"],[2,2,1,"","path"],[2,2,1,"","repository_memberships"],[2,2,1,"","sha256sum"],[2,2,1,"","size"],[2,2,1,"","unit_id"],[2,2,1,"","version"]],"pubtools.pulplib.MaintenanceEntry":[[3,2,1,"","message"],[3,2,1,"","owner"],[3,2,1,"","repo_id"],[3,2,1,"","started"]],"pubtools.pulplib.MaintenanceReport":[[3,1,1,"","add"],[3,2,1,"","entries"],[3,2,1,"","last_updated"],[3,2,1,"","last_updated_by"],[3,1,1,"","remove"]],"pubtools.pulplib.Matcher":[[5,1,1,"","equals"],[5,1,1,"","exists"],[5,1,1,"","in_"],[5,1,1,"","less_than"],[5,1,1,"","regex"]],"pubtools.pulplib.ModulemdDefaultsUnit":[[7,2,1,"","name"],[7,2,1,"","profiles"],[7,2,1,"","repo_id"],[7,2,1,"","repository_memberships"],[7,2,1,"","stream"],[7,2,1,"","unit_id"]],"pubtools.pulplib.ModulemdDependency":[[7,2,1,"","name"],[7,2,1,"","stream"]],"pubtools.pulplib.ModulemdUnit":[[7,2,1,"","arch"],[7,2,1,"","artifacts"],[7,3,1,"","artifacts_filenames"],[7,2,1,"","context"],[7,2,1,"","dependencies"],[7,2,1,"","name"],[7,3,1,"","nsvca"],[7,2,1,"","profiles"],[7,2,1,"","repository_memberships"],[7,2,1,"","stream"],[7,2,1,"","unit_id"],[7,2,1,"","version"]],"pubtools.pulplib.Page":[[5,2,1,"","data"],[5,2,1,"","next"]],"pubtools.pulplib.PublishOptions":[[4,2,1,"","clean"],[4,2,1,"","force"],[4,2,1,"","origin_only"],[4,2,1,"","rsync_extra_args"]],"pubtools.pulplib.PulpObject":[[4,1,1,"","from_data"]],"pubtools.pulplib.Repository":[[4,2,1,"","content_set"],[4,2,1,"","created"],[4,1,1,"","delete"],[4,1,1,"","distributor"],[4,2,1,"","distributors"],[4,2,1,"","eng_product_id"],[4,3,1,"","file_content"],[4,2,1,"","id"],[4,2,1,"","is_sigstore"],[4,2,1,"","is_temporary"],[4,3,1,"","modulemd_content"],[4,3,1,"","modulemd_defaults_content"],[4,2,1,"","mutable_urls"],[4,1,1,"","publish"],[4,2,1,"","relative_url"],[4,1,1,"","remove_content"],[4,3,1,"","rpm_content"],[4,1,1,"","search_content"],[4,2,1,"","signing_keys"],[4,2,1,"","skip_rsync_repodata"],[4,3,1,"","srpm_content"],[4,1,1,"","sync"],[4,2,1,"","type"]],"pubtools.pulplib.RpmDependency":[[7,2,1,"","epoch"],[7,2,1,"","flags"],[7,2,1,"","name"],[7,2,1,"","release"],[7,2,1,"","version"]],"pubtools.pulplib.RpmUnit":[[7,2,1,"","arch"],[7,2,1,"","cdn_path"],[7,2,1,"","cdn_published"],[7,2,1,"","epoch"],[7,2,1,"","filename"],[7,2,1,"","md5sum"],[7,2,1,"","name"],[7,2,1,"","provides"],[7,2,1,"","release"],[7,2,1,"","repository_memberships"],[7,2,1,"","requires"],[7,2,1,"","sha1sum"],[7,2,1,"","sha256sum"],[7,2,1,"","signing_key"],[7,2,1,"","sourcerpm"],[7,2,1,"","unit_id"],[7,2,1,"","version"]],"pubtools.pulplib.SyncOptions":[[4,2,1,"","basic_auth_password"],[4,2,1,"","basic_auth_username"],[4,2,1,"","feed"],[4,2,1,"","max_speed"],[4,2,1,"","proxy_host"],[4,2,1,"","proxy_password"],[4,2,1,"","proxy_port"],[4,2,1,"","proxy_username"],[4,2,1,"","ssl_ca_cert"],[4,2,1,"","ssl_client_cert"],[4,2,1,"","ssl_client_key"],[4,2,1,"","ssl_validation"]],"pubtools.pulplib.Task":[[4,2,1,"","completed"],[4,2,1,"","error_details"],[4,2,1,"","error_summary"],[4,2,1,"","id"],[4,2,1,"","repo_id"],[4,2,1,"","succeeded"],[4,2,1,"","tags"],[4,2,1,"","units"],[4,2,1,"","units_data"]],"pubtools.pulplib.TaskFailedException":[[0,2,1,"","task"]],"pubtools.pulplib.Unit":[[4,2,1,"","content_type_id"]],"pubtools.pulplib.YumRepoMetadataFileUnit":[[7,2,1,"","data_type"],[7,2,1,"","repository_memberships"],[7,2,1,"","sha256sum"],[7,2,1,"","unit_id"]],"pubtools.pulplib.YumRepository":[[7,1,1,"","get_binary_repository"],[7,1,1,"","get_debug_repository"],[7,1,1,"","get_source_repository"],[7,2,1,"","population_sources"],[7,2,1,"","ubi_config_version"],[7,2,1,"","ubi_population"],[7,1,1,"","upload_comps_xml"],[7,1,1,"","upload_erratum"],[7,1,1,"","upload_metadata"],[7,1,1,"","upload_modules"],[7,1,1,"","upload_rpm"]],"pubtools.pulplib.YumSyncOptions":[[7,2,1,"","allowed_keys"],[7,2,1,"","checksum_type"],[7,2,1,"","download_policy"],[7,2,1,"","force_full"],[7,2,1,"","max_downloads"],[7,2,1,"","num_retries"],[7,2,1,"","query_auth_token"],[7,2,1,"","remove_missing"],[7,2,1,"","require_signature"],[7,2,1,"","retain_old_count"],[7,2,1,"","skip"]]},objnames:{"0":["py","class","Python class"],"1":["py","method","Python method"],"2":["py","attribute","Python attribute"],"3":["py","property","Python property"]},objtypes:{"0":"py:class","1":"py:method","2":"py:attribute","3":"py:property"},terms:{"0":[0,2,3,4,5,6,7,10],"00":5,"00z":5,"05t11":10,"06":[7,10],"0672":7,"07":10,"08":5,"0c":7,"1":[0,2,3,4,5,6,7,9],"10":[2,9],"10aa":9,"12":[0,7],"14":5,"16":7,"17":[0,7],"19":0,"2":[0,2,4,5,6,7,9,10],"20":[0,2,7],"201801":7,"20180813043155":7,"2019":[5,7,10],"2021":7,"21":6,"23":2,"24":7,"27":5,"27t00":5,"3":[4,5,7,9],"31":7,"32":10,"36be54431bd":9,"39":9,"39b9":10,"4":[0,2,3,4,6,7,10],"40":10,"4004":9,"401":9,"40f9":9,"41":7,"441":7,"46f0":10,"49ae93732fcf8d63fe1cce759664982dbd5b23161f007dba8561862adc96d063":5,"5":[2,4,6,7],"50z":10,"512251904":10,"522a0ee4":7,"54":7,"54ba8e8c":9,"56":10,"6":[0,2,7],"64":10,"6718":7,"69759d0fb9a16c0a47b1f49c78f6712e650912e1":10,"6b30e91df993d96df0bef0f9d232d1068fa2f7055f13650208d77b43cd7c99f6":5,"7":[4,7],"7744e2df":10,"7f269185":7,"7fad":9,"8":[2,5],"8040020210622174547":7,"8e06f17d22ef":9,"9":10,"99":7,"boolean":[7,10],"byte":[2,4,7,10],"case":[0,2],"catch":10,"class":[0,1,2,3,4,6,7],"const":10,"default":[2,4,7],"do":[4,6],"enum":10,"final":7,"function":6,"import":[1,2,7,8,10],"int":0,"new":[0,2,3,4,5,6,7],"null":10,"public":[6,10],"return":[0,2,3,4,5,7,8,10],"short":[4,7,10],"true":[2,4,5,7,10],"while":[0,6,7],A:[0,1,2,3,4,5,6,7,8,9,10],As:7,At:5,For:[0,1,2,4,5,7,9,10],If:[0,2,3,4,5,7,9,10],In:[0,2,7,8],It:[5,6,7],No:5,On:[3,7],Or:2,Such:4,That:7,The:[0,1,2,4,5,6,7,9,10],There:[5,7],These:[0,4,9,10],To:4,Will:5,With:5,_base:5,_content_type_id:10,_id:10,_repo:10,a9a9:9,aarch64:7,abc:5,abil:[2,6,7],abl:5,about:[3,5],abov:[5,10],accept:10,access:[0,2,7],accident:7,across:[0,5],action:[0,4,6,8],activ:0,actual:10,ad:[2,3,6,7],add:[3,6],addit:[2,4,7],address:7,admin:8,advis:7,advisori:7,affect:10,after:[2,7],against:[4,5,6,7],algorithm:10,alia:7,all:[0,4,5,6,7,8,10],allof:10,allow:[0,5,6,7,10],allowed_kei:7,along:7,alongsid:7,alreadi:7,also:[4,10],altern:[0,7],alwai:5,an:[0,2,4,5,7,9,10],analog:7,anchor:5,and_:5,ani:[0,2,4,5,6,7,10],anoth:[0,7],anyof:10,api:[8,9,10],appear:0,appli:[4,5,7],applic:[4,7],appropri:[4,5,6,7],approxim:[2,7],ar:[0,3,4,5,7,9,10],arbitrari:[4,5,7,10],arbitrarili:7,arch:[7,10],architectur:[7,10],argument:[0,4],arrai:10,artifact:[7,10],artifacts_filenam:7,ascend:2,assert:6,assoc:10,associ:[0,2,4,7,10],asynchron:0,atom:7,attach:[0,2,4,6,7],attempt:[0,2,4,5,7,9],attr:[1,2,3,4,5,7],attribut:[0,2,4,6,7,9],auth:[0,8],authent:4,author:7,autom:6,av:7,avail:[0,2,4,7],avoid:[5,7],await:[0,4,5,9],awar:7,b:5,back:7,background:7,backtrac:4,bar:2,base:4,basenam:[2,7],bash:7,basic:4,basic_auth_password:4,basic_auth_usernam:4,bb10:10,becam:[2,7],becom:4,been:[0,2,4,7,10],befor:[0,2,5,7,9],behavior:4,being:[7,9,10],belong:[4,7],bewar:7,bfb6:9,binari:7,blank:7,blob:10,block:[0,3,5,8],both:[2,4,5,10],bound:7,boundari:5,brief:4,briefli:7,bug:7,bugfix:7,bugzilla:7,built:7,bundl:0,bytewis:7,c:5,ca:[0,4],call:[0,4,5,8],caller:[4,5],can:[0,2,6,7],cancel:[0,9,10],cannot:[0,7],canon:7,capabl:7,care:[7,10],cdn:[2,7,10],cdn_path:[0,2,7],cdn_publish:[2,7],cert:0,certain:[4,5,10],certif:[4,7],chain:5,chang:4,check:3,checksum:[2,7,10],checksum_typ:7,cl:4,claim:6,clash:7,classmethod:[4,5],clean:4,client:[1,2,4,5,6,7,8,9],close:[2,7],code:[0,5,6,8,10],collect:[0,4,7],com:[0,1,4,8,9,10],come:7,comma:10,command:[4,9],common:[0,2,5],commonli:7,comp:7,comparison:5,compat:5,complet:[0,2,4,7,9,10],compon:[2,10],compos:5,concurr:5,config:[7,10],configur:[0,4],conjunct:5,connect:[0,4],consid:[9,10],consist:[4,7],construct:[7,8],contact:7,contain:[0,2,4,5,6,7,8],containerimagerepositori:1,containersyncopt:[1,4],content:[0,2,4,5,6,7,10],content_set:[4,10],content_typ:7,content_type_id:[4,6],context:[0,7,10],control:[1,2,4,6,7],convent:10,copi:[0,3],copy_cont:0,copyright:7,core:8,correspond:[3,7],count:[7,9],crash:6,creat:[3,4,5,6,9,10],creation:10,credenti:0,crit:5,criteria:[0,4,5],critic:7,current:[0,3,6,7,9],custom:[4,10],dai:[4,6],data:[0,4,5,6,7,10],data_typ:7,databas:[5,6],date:5,datetim:[2,3,4,5,6,7],dca7b4a4:7,debug:7,debuginfo:7,decid:10,declar:7,def:[5,6],defin:[4,5,7],definit:10,delet:[4,6,10],delete_old_repo:6,denot:4,depend:[0,5,7,10],deprec:4,describ:[0,7],descript:[2,7,10],desir:8,detach:4,detachedexcept:[0,2,4,7],detail:[0,3,4,5,10],determin:[0,4],dev:10,dict:[4,10],did:10,differ:10,direct:5,directli:[4,5,7],directori:2,disc2:10,displai:[2,4],display_ord:2,distribut:[2,4],distributor:[0,4,10],distributor_id:4,distributor_type_id:10,dnf:7,do_someth:5,do_something_with:0,doc:10,docker:1,document:[0,2,5,7,10],doe:7,doesn:3,don:10,done:5,down:0,download:[2,4,7],download_polici:7,draft:10,drpm:7,due:[0,9],duplic:10,dure:[0,4,5,7,10],e239ae4f:9,e:[0,1,2,4,5,6,7,8,10],each:[0,4,6,7,10],effect:[0,7],efi:7,either:[0,2,7],el7:7,el8:7,element:[4,6,10],elsewher:[2,7],email:7,empti:3,enabl:9,encapsul:8,encourag:0,end:10,enforc:7,eng_product:5,eng_product_id:[4,5],engin:[3,4,10],enhanc:7,ensur:[0,7],entri:[3,7],envr:10,epoch:[7,10],eq:[5,7],equal:[5,7],equival:5,eras:4,erratum:[0,6,7,10],erratummodul:7,erratumpackag:7,erratumpackagecollect:7,erratumrefer:7,erratumunit:7,error:[2,5,7,9,10],error_detail:4,error_summari:4,even:4,event:9,everi:[3,4,5,7,9],everywher:5,evolv:4,exactli:[4,5],exampl:[0,1,2,4,5,6,7,8,9,10],except:[0,5,7,10],execut:[5,7,10],exist:[0,3,5,6,7],expect:[0,4,7,10],explain:7,explicitli:4,expos:4,express:5,extens:7,extern:[3,4,10],f0:10,f:2,f_flat_map:5,f_return:5,fail:[0,4,9,10],failur:[0,4],fake:6,fakecontrol:6,famili:4,fatal:9,fc30:7,fedora:1,feed:[4,7],feffa2f7014b:10,fetch:0,few:[4,9],field:[0,2,6,7,10],field_nam:5,field_valu:5,file:[4,7,8,10],file_cont:4,file_obj:[2,7],filenam:[7,10],filerepositori:[2,6],filesyncopt:[2,4],fileunit:[2,4],find:[0,5,6,7],finish:10,first:[0,2,3,4,7],flag:[7,10],follow:[6,7,9],foo:2,forc:[4,10],force_ful:7,form:[7,9],format:[7,10],formerli:4,found:7,fragment:5,friend:5,from:[0,1,2,3,4,5,7,8,10],from_:7,from_data:[4,10],from_repositori:0,full:[2,7],further:4,futur:[0,2,4,5,7,8],g:[0,2,4,5,6,7,8,10],ge:7,gener:[0,1,2,3,4,5,6,7,9,10],get:[0,4,8],get_binary_repositori:7,get_content_type_id:[0,4],get_debug_repositori:7,get_maintenance_report:0,get_repositori:[0,8],get_source_repositori:7,github:10,given:[0,4,5,6,7],gnu:7,gpg:[4,7,10],greater:7,group:[2,7],gt:7,guarante:[3,7],guid:10,gz:2,ha:[0,2,4,5,6,7,10],handl:[4,5],handle_result:5,handled_f:5,have:[0,2,4,6,7,8,10],header:0,helper:4,here:[2,6,7],hex:[2,7,10],hierarchi:5,high:0,hint:2,hold:[0,3],host:[4,7],how:7,howev:[2,5,7],href:7,html:[7,10],http:[0,4,8,9,10],human:7,i:[0,1,7],ia64:10,id:[0,1,2,3,4,5,6,7,8,10],ideal:10,idempot:0,ident:7,identifi:[7,10],ignor:[4,7],imag:[1,4],imagin:6,immedi:7,immut:4,impact:[4,7],implement:[5,6],impli:[4,7],implicitli:[5,9],in_:5,includ:[1,2,4,5,7,9,10],incomplet:7,inconsist:7,increment:7,index:10,indic:[2,3,4,5,7,9,10],individu:3,info:[0,4,9],inform:[2,3,4,5,7],initi:[0,7,10],inner:10,input:5,insert:6,insert_repositori:6,insert_task:6,insert_unit:6,inspect:[0,6],instal:[0,2,4,7,8],instanc:[0,2,4,5,6,7,8],instanti:4,instead:[4,7],integ:[4,7,10],intend:5,intent:10,interest:9,interfac:6,intern:0,interrupt:7,invalid:0,invaliddataexcept:[0,4],invok:4,io:1,is_rsync:4,is_sigstor:4,is_temporari:4,iso8601:10,iso:10,iso_distributor:10,issu:[4,5,6,7],item:10,iter:[4,5],itself:[7,10],javapackag:7,join:0,json:[4,10],just:10,kei:[4,7,10],keyword:7,kind:7,known:[0,2,4,6,7],kwarg:[0,2,3,4,7],l436:10,larg:4,larger:7,last:[3,4,5,7,10],last_publish:[4,5,10],last_upd:[3,10],last_updated_bi:[3,10],later:10,latest:1,le:7,lead:2,least:[2,4,7],left:7,less:[4,5,7],less_than:5,level:[0,9],librari:[0,5,6,7,8,9,10],lifecycl:0,lifetim:4,like:[2,6,7],limit:6,line:[4,7,10],linux:2,list:[0,1,2,3,4,5,6,7,10],ll:10,load:9,local:2,locat:7,log:[0,8],logger:9,longer:4,look:4,lookup:0,loop:5,low:7,lt:7,machin:7,made:[7,9],mai:[0,2,4,5,6,7,8,9,10],mainten:[0,8],maintenanceentri:3,maintenancereport:[0,3],major:4,make:[3,4,8],malici:7,manag:0,mandat:10,mandatori:[0,2,10],mani:[7,9],manifest:4,map:5,match:[0,3,4,5],matcher:5,matter:[2,10],max_download:7,max_redirect:0,max_spe:4,maximum:[0,4,9],md5:[7,10],md5sum:7,mean:[0,3,7,10],memori:6,mention:10,merg:7,messag:[3,7,9,10],metadata:4,metadata_typ:7,method:[0,1,2,3,4,5,7,8,9,10],min:6,minut:9,mod_security_cr:7,mode:[0,3,10],model:4,moder:7,modifi:[2,6,7],modular:7,modulemd:[0,4,7,10],modulemd_cont:4,modulemd_default:[4,7,10],modulemd_defaults_cont:4,modulemddefaultsunit:[4,7],modulemddepend:7,modulemdunit:[4,7],mongo:[5,10],more:[0,4,5,8],most:[0,6,7],much:7,multi:[4,10],multipl:[7,10],must:[0,2,4,5,7,10],mutabl:[0,2,7],mutable_url:4,mutat:7,my:[5,10],name:[1,2,4,5,6,7,10],necessari:4,need:[0,5],nest:5,never:10,nevra:7,newest:0,next:5,noarch:7,non:[5,7,10],none:[0,2,3,4,5,6,7],note:[0,3,5,7,10],noth:[3,5],now:[5,6],nowadai:10,nsvca:[7,10],num_retri:7,number:[0,5,6,7,9,10],object:[0,2,3,4,5,6,7,8,10],observ:10,obtain:[4,5],oc:2,occur:[2,5,7,9],often:4,old:[2,6,7,10],older:6,omit:[2,4],on_demand:7,onc:[0,2,7],one:[0,2,4,5,7,8,10],onli:[0,2,4,5,6,7,10],opaqu:5,openscap:1,openshift:2,oper:[0,3,4,5,7,9,10],oppos:7,opt:4,option:[1,2,3,4,5,7,10],or_:5,order:[2,4,6,10],org:10,orient:2,origin:[4,10],origin_onli:4,orphan:6,other:[0,2,3,5,7,9,10],otherwis:[2,4,5,7],out:4,outstand:0,over:[0,5],overload:0,overwhelm:0,overwrit:7,overwritten:7,owner:[3,7,10],ownership:[2,7],packag:7,page:[0,4,5,7],page_f:5,pagin:5,pair:10,param:0,paramet:[0,2,3,4,5,6,7],pars:7,parser:7,part:[4,10],parti:3,particular:8,pass:2,password:[4,8],path:[2,4,7,10],pattern:[5,10],patternproperti:10,pcre:5,per:[7,10],perform:[0,4,8],perl:7,permit:0,persist:0,person:[3,10],pick:10,piec:4,pip:8,pkglist:7,plain:4,pleas:7,plp0018:10,plugin:[0,4,10],point:[2,5,7,8],polici:7,popul:[7,10],population_sourc:[7,10],port:4,portabl:5,possibl:[3,4,5],practic:7,prefer:5,present:[4,5,7,10],print:5,privat:4,probabl:10,proce:7,process:[4,5,7],produc:[0,4,9],product:[2,4,7],productid:7,profil:[7,10],progress:9,promptli:0,properti:[4,6,7,10],protocol:0,provid:[0,4,6,7,10],proxi:[0,4],proxy_host:4,proxy_password:4,proxy_port:4,proxy_usernam:4,pub_temp_repo:10,publish:[0,1,2,3,4,6,7,8,10],publish_histori:6,publish_task:0,publishopt:4,pubtool:[0,1,2,3,4,5,6,7,9],pull:1,pulp2:10,pulp:[0,1,2,3,4,6,7,8,10],pulp_rpm:10,pulpexcept:0,pulplib:[0,1,2,3,4,5,6,7,9],pulpobject:[4,5],pulpproject:10,purpos:[2,7,9],pushcount:7,put:3,py:10,pypi:8,python:[4,5,7,8,10],quai:1,queri:[0,5],query_auth_token:7,queu:0,queue:0,quirk:7,rais:[0,2,4,5,7,10],rather:[4,6],raw:[0,4],re:[0,5,7,10],readabl:7,readi:5,real:6,reason:[3,4],reboot:7,reboot_suggest:7,receiv:0,recent:6,recommend:[5,7,9],record:10,redhat:1,reduc:7,ref:10,refer:[7,10],referenc:7,regex:5,registri:1,registry_id:1,regular:5,rel:[2,4,7,10],relat:[2,7],relative_url:[2,4,10],releas:[3,4,7,10],relev:[4,8],remain:3,remot:[2,4,6],remov:[2,3,4,7],remove_cont:4,remove_miss:[2,7],render:[4,7],repo:[0,1,2,3,4,5,6,7,8,10],repo_id:[0,3,4,7,10],repo_now:6,repo_old:6,repodata:[7,10],report:[0,3,10],repositori:[0,3,5,6,9],repository_id:0,repository_membership:[2,7,10],repres:[0,2,3,4,5,7],represent:4,reproduc:7,republish:7,request:[0,4,6,7],requir:[0,5,7,10],require_signatur:7,resolv:[0,2,4,5,7],respect:7,respond:0,respons:[0,3],result:[0,2,4,5,6,7,8,10],retain:7,retain_old_count:7,retri:[0,7],revis:7,rhel4:10,rhel7:1,rhel:[4,7],rhsa:7,rhsm:7,right:7,risk:7,root:[2,4,7,10],roughli:5,rpm:[0,4,6,10],rpm_content:4,rpm_rsync_distributor:4,rpmdepend:7,rpms__7server__x86_64:7,rpms__7server_x86_64:4,rpmunit:[4,5,7],rsync:[4,10],rsync_extra_arg:4,run:[0,4,6,9,10],runtim:7,s:[0,2,3,4,5,6,7,9,10],same:[2,5,6,7],satisfi:5,scatter:0,schema:[0,4,6,8],scriplet:7,search:[0,4,6,7,8,9,10],search_cont:[0,4,5],search_distributor:0,search_repositori:[0,5],search_task:0,sec:4,secur:7,see:[4,5,10],self:7,sens:4,sent:9,sentenc:7,separ:10,sequenc:4,server:[0,3,4,6,7,8,10],session:0,set:[0,1,2,3,4,5,6,7,10],set_content_type_id:6,set_mainten:0,sever:[0,7],sha1:[7,10],sha1sum:7,sha256:[2,7,10],sha256sum:[2,5,7],share:7,should:[1,2,4,5,6,7,10],show:[9,10],shut:0,sign:[4,7,10],signatur:[4,7,10],signing_kei:[4,7,10],sigstor:4,simpl:6,sinc:[4,10],singl:[0,4,5,7,10],size:[2,10],skip:[4,7,10],skip_repodata:10,skip_rsync_repodata:4,so:[0,4,10],sole:7,solut:7,some:[0,4,8,10],sourc:[0,1,2,3,4,5,6,7,10],sourcerpm:[7,10],spawn:0,specif:[2,3,4,5,7],specifi:[4,5],speed:4,sqlite:7,src:7,srpm:[0,4,7,10],srpm_content:4,ssl:4,ssl_ca_cert:4,ssl_client_cert:4,ssl_client_kei:4,ssl_valid:4,start:[3,5,7,10],state:[4,7,10],statement:0,statu:[0,3,7],step:[4,7],still:9,store:[4,7,10],str:[0,2,3,4,5,6,7],stream:[7,10],string:[2,4,5,7,10],strongli:7,style:[5,7],subclass:[0,4,5,6],subsequ:5,subset:[0,5],succe:[4,6,9],succeed:[0,4],successfulli:[0,4,7,10],suggest:2,suitabl:4,sum:5,summari:[4,7,10],superset:4,support:[0,4,5,6,7,10],suppos:10,sure:3,sync:[1,2,4,6,7],sync_config:6,sync_histori:6,syncconfig:6,synchron:[0,2,4,7],syncopt:4,syntax:5,system:7,t:[0,3,10],tag:[1,4,10],take:[2,7],tar:2,target:7,task:[0,2,6,7,8],task_id:[0,10],task_throttl:0,taskfailedexcept:0,technic:4,temporari:[4,10],ters:2,test:8,test_delete_old_repo:6,text:7,than:[0,4,5,6,7],thei:10,them:10,therefor:7,thi:[0,1,2,3,4,5,6,7,8,9,10],those:0,though:[4,7,10],thread:[0,7],throttl:0,through:5,throughout:0,time:[0,3,7,9,10],timestamp:[3,7,10],titl:[7,10],to_repositori:0,togeth:2,token:7,too:5,tool:[4,7,8,10],traceback:10,trigger:[0,4,6,7],triplet:7,tupl:6,two:5,txt:2,type:[0,4,5,6,7,9,10],type_id:[4,6,10],typic:[0,4,7],u5:10,ubi:[7,10],ubi_config_vers:[7,10],ubi_popul:[7,10],ui:2,unassoc:10,unassoci:4,unauthor:9,unavail:[2,4,7],under:6,understood:10,uniqu:[2,7],unit:[0,5,6],unit_id:[0,2,7],unit_kei:[4,10],unit_typ:5,units_data:4,units_success:10,unknown:[4,10],unless:7,unlik:7,unrecover:0,unset:3,unsuccessfulli:10,unsupport:5,up:[4,5,10],updat:[0,3,4,7,10],update_cont:[0,2,7],upload:[0,2,4,7,10],upload_comps_xml:7,upload_erratum:7,upload_fil:2,upload_metadata:7,upload_modul:7,upload_rpm:7,upstream:1,upstream_nam:1,url:[0,4,7,8,9,10],us:[0,1,2,3,4,5,6,7,10],usag:0,user:[2,3,4,10],usernam:4,usual:7,utc:[2,3,4,7],utcnow:6,v1:7,v2:[4,7,9,10],valid:[4,5,7,10],valu:[0,2,4,5,7,10],variou:[7,9],verifi:[0,4],version:[0,2,3,4,5,6,7,10],via:[0,2,4,5,6,7],virt:7,wa:[3,4,6,7,10],wait:[0,10],want:7,warn:[7,9],we:[5,6,10],were:[0,4,10],what:[2,10],when:[0,2,3,4,5,7,9,10],whenev:7,where:[2,4,5,10],whether:7,which:[0,2,3,4,5,6,7,9,10],who:[3,4,10],whose:5,why:[3,10],with_field:5,with_id:5,with_unit_typ:5,within:[0,4,5,6,7],without:[0,2,6,7],wll:2,won:10,work:10,worker:10,workflow:[4,10],wors:7,would:[5,10],written:0,x86_64:7,x:[0,4,5,7,10],xml:7,yaml:7,you:[5,7],your:[5,8],yum:[4,8,10],yum_distributor:[4,10],yumrepometadatafileunit:7,yumrepositori:[6,7],yumsyncopt:[4,7],z:10,zero:4,zoo:[4,8,10]},titles:["API: client","API: containers","API: files","API: maintenance","API: core","API: searching","API: testing","API: yum","pubtools-pulplib","Logging","Schemas"],titleterms:{"class":5,"function":4,api:[0,1,2,3,4,5,6,7],chang:9,client:0,common:4,contain:1,content:8,core:4,errata:7,error:0,field:5,file:2,log:9,mainten:[3,10],metadata:7,model:5,modul:7,pubtool:8,pulp:[5,9],pulplib:8,quick:8,refer:5,repositori:[1,2,4,7,10],retri:9,rpm:7,schema:10,search:5,start:8,state:9,task:[4,9,10],test:6,unit:[2,4,7,10],vs:5,wait:9,yum:7}})