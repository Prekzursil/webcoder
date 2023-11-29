$(function(){function format(state){if(!state.id)return state.text;return state.text;}
window.previous_template='';function update_language_template(){var source=$('textarea#id_source');if(source.val()==window.previous_template.replace(/\r/g,'')||source.val()==''){var lang_id=$('#id_language').val();var code=localStorage.getItem('submit:'+$('#id_language').val());function update_submit_area(code){window.previous_template=code;source.val(code);window.ace_source.getSession().setValue(code);}
if(code!=null){update_submit_area(code);}else{$.get('/widgets/template',{id:lang_id}).done(function(template){update_submit_area(template);});}}}
function makeDisplayData(data){var site_data=data.attr('data-info');var judge_data=data.attr('data-judge-info');var display_data=site_data||judge_data;return display_data;}
function formatSelection(state){if(!state.id)return state.text;var data=makeDisplayData($("option[data-id="+state.id+"]"));return"<b>"+state.text+"</b> ("+data+")";}
$.fn.select2.amd.define('select2/data/customAdapter',['select2/results','select2/utils'],function(Result,Utils){RefPresenter=function($element,options,dataAdapter){RefPresenter.__super__.constructor.call(this,$element,options,dataAdapter);};Utils.Extend(RefPresenter,Result);RefPresenter.prototype.bind=function(container,$container){container.on('results:focus',function(params){var data=makeDisplayData($("option[data-id="+params.data.id+"]"));$("#result-version-info").text(data);});RefPresenter.__super__.bind.call(this,container,$container);};return RefPresenter;});var customAdapter=$.fn.select2.amd.require('select2/data/customAdapter');$('#id_theme').select2();$("#id_language").select2({templateResult:format,templateSelection:formatSelection,escapeMarkup:function(m){return m;},resultsAdapter:customAdapter});$('#id_language').on('select2:open',function(evt){var dropdown=$('.select2-dropdown');if(!$('#result-version-info').length)
dropdown.append($("<span id=\"result-version-info\">"));dropdown.attr('id','language-select2');});$('#id_judge').on('select2:open',function(evt){var dropdown=$('.select2-dropdown');$('#result-version-info').remove();dropdown.attr('id','judge-select2');});$('#id_language').change(function(){var lang=$("#id_language").find("option:selected").attr('data-ace');window.ace_source.getSession().setMode("ace/mode/"+lang);update_language_template();});$('#id_theme').change(function(){var theme=$("#id_theme").find("option:selected");window.ace_source.setTheme('ace/theme/'+theme[0].value);window.ace_source.setFontSize(18);});$('#ace_source').on('ace_load',function(e,editor){update_language_template();editor.commands.addCommand({name:'save',bindKey:{win:'Ctrl-S',mac:'Command-S'},exec:function(){localStorage.setItem('submit:'+$('#id_language').val(),editor.getSession().getValue());}});editor.getSession().setUseWrapMode(true);editor.setFontSize(18);editor.setPrintMarginColumn(100);editor.focus();});$(window).resize(function(){$('#ace_source').height(Math.max($(window).height()-353,100));}).resize();$('#problem_submit').submit(function(event){if($('#id_source').val().length>65536){alert("Your source code must contain at most 65536 characters.");event.preventDefault();$('#problem_submit').find(':submit').attr('disabled',false);}});});;