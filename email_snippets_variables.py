EMAIL_BODY = '''
<!DOCTYPE html>
<html lang="en">
   <head>
      <meta charset="UTF-8">
      <style type="text/css">
         body{font-family: Arial, sans-serif; font-size:13px}
         tbody{font-family: Arial, sans-serif}
         .tg  {border-collapse:collapse;border-spacing:0;}
         .tg td{border-color:black;border-style:solid;border-width:1px;font-family:Arial, sans-serif;font-size:10px;
         overflow:hidden;padding:2px;word-break:normal;}
         .tg th{border-color:black;border-style:solid;border-width:1px;font-family:Arial, sans-serif;font-size:10px;
         font-weight:normal;overflow:hidden;padding:2px;word-break:normal;}
         .tg .tg-pb0m{border-color:inherit;text-align:center;vertical-align:bottom}
         .tg .tg-9wq8{border-color:inherit;text-align:center;vertical-align:middle}
         .tg .tg-uzvj{border-color:inherit;font-weight:bold;text-align:center;vertical-align:middle}
         .tg .tg-za14{border-color:inherit;text-align:left;vertical-align:bottom}
         .tg .tg-u7ol{background-color:#343434;border-color:inherit;color:#f8ff00;font-weight:bold;text-align:left;vertical-align:bottom}
         .tg {margin-left: 20px}
      </style>
   </head>
   <body>
      <table width="100%" cellpadding="12" cellspacing="0" border="0">
         <tr>
            <td>
               <div style="overflow: hidden;">
                  <font size="-1">
                     <div>
                        <b>Título: </b><!--MONITORING_TITLE-->
                     </div>   
                     <div>
                        <b>Descrição: </b><!--MONITORING_DESCRIPTION-->
                     </div>
                     <div>
                        <b>Tipo da monitoria: </b>Monitoria sobre <!--MONITORING_TYPE-->
                     </div>
                     <div>
                        <b>Controle(s) monitorado(s): </b><!--CONTROL--><br>
                     </div>
                     <br>
                     <hr>
                     <br>
                     <!--MISSING_CONTROL-->
                     <!--MODIFIED_CONTROLS-->
                     <!--FILTERS_MONITORING_INTRODUCTION-->
                     <!--NEW_CONDITIONS-->
                     <!--MISSING_CONDITIONS-->
                     <!--REPLACED_CONDITIONS-->
                  </font>
               </div>
           </tr>
       </table>
      </table>
   </body>
</html>
'''

MISSING_CONTROLS_HTML = '''
<div><font size="4"><b>Saída de controle(s) monitorado(s)&nbsp;</b></font></div>
<div>Não foram identificados um ou mais controles monitorados. Abaixo seguem os controles não encontrados.</div>
<div>
   <ul>
      LIST_ITEM
   </ul>
</div>
<!--CONTROLS_WERE_REMOVED-->
<div><br></div>
<div><br></div>
'''

CONTROLS_WERE_REMOVED_FROM_MONITORING = '<div>Os controles não encontrados foram removidos de sua lista de controles monitorados.</div>'
REMOVED_MODIFIED_CONDITIONS_CONTROLS = '<div>Os controles com condições alteradas foram removidos da sua lista monitorada.</div>'

HTML_UL = '''
<div>
   <div><font size="4"><b>Alteração em controle monitorado</b></font></div>
   <div>Um ou mais dos controles monitorados sofreram alterações. Abaixo seguem as alterações identificadas.</div>
   <div>
      <!--MODIFIED_CONTROLS_LIST-->
      <!--CONTROLS_WERE_MODIFIED-->
   </div>
</div>
<div><br></div>
<div><br></div>
'''

COMPARISON_TABLE = '''
<table class="tg">
   <thead>
      <tr>
         <th class="tg-9wq8"></th>
         <!--TABLE_HEADERS-->
      </tr>
   </thead>
   <tbody>
      <tr>
         <td class="tg-pb0m">Registro anterior</td>
         <!--PREVIOUS_RECORD_TDS-->
      </tr>
      <tr>
         <td class="tg-pb0m">Registro atual</td>
         <!--CURRENT_RECORD_TDS-->
      </tr>
   </tbody>
</table>
'''

MODIFIED_CONTROLS_LIST = '''
<ul>
<li>Controle: <b><!--CONTROL--></b></li>
<li>Alteração: <!--CONTROL_MODIFICATION--></li>
</ul>
<!--COMPARISON_TABLE-->
<div><br></div>
'''


MODIFIED_CONDITION_PARAGRAPH = '<p>Foram identificadas alterações sobre sua monitoria de filtros. Isto indica que registros monitorados anteriormente podem não estar mais incluídos na lista de filtros, tendo sido excluídos, alterados, ou criados. Sua lista de filtros está indicada abaixo:</p>\n'

NEW_CONDITION_FOUND = '''
<div>
    <br>
   <div><font size="4"><b>Novo(s) controle(s) identificado(s)</b></font></div>
      <!--NEW_CONTROLS_TABLE-->
   </div>
</div>
<div><br></div>
<div><br></div>
'''

MISSING_CONDITION_FOUND = '''
<div>
   <br>
   <div><font size="4"><b>Controle(s) não encontrado(s) ou alterado(s) </b></font></div>
      <br>Não encontrado(s) na filtragem:<br>
      <!--MODIFIED_CONDITIONS_TABLE-->          
      <!--MODIFIED_CONDITIONS_NEW_PLACEMENT-->
   </div>
</div>
<div><br></div>
<div><br></div>
'''

MODIFIED_CONDITIONS_TABLE = '''
<table class="tg">
   <thead>
      <tr>
         <!--TABLE_HEADERS-->
      </tr>
   </thead>
   <tbody>
     <!--MODIFIED_RECORDS_TRS-->
   </tbody>
</table>
'''


snippets = {
    "TITLE": "Sua monitoria encontrou alterações: ",
    "EMAIL_BODY": EMAIL_BODY,
    "MISSING_CONTROLS_HTML": MISSING_CONTROLS_HTML,
    "CONTROLS_WERE_REMOVED_FROM_MONITORING": CONTROLS_WERE_REMOVED_FROM_MONITORING,
    "REMOVED_MODIFIED_CONDITIONS_CONTROLS": REMOVED_MODIFIED_CONDITIONS_CONTROLS,
    "HTML_UL": HTML_UL,
    "COMPARISON_TABLE": COMPARISON_TABLE,
    "MODIFIED_CONTROLS_LIST": MODIFIED_CONTROLS_LIST,
    "MODIFIED_CONDITION_PARAGRAPH": MODIFIED_CONDITION_PARAGRAPH,
    "NEW_CONDITION_FOUND": NEW_CONDITION_FOUND,
    "MISSING_CONDITION_FOUND": MISSING_CONDITION_FOUND,
    "NEW_CONDITION_FOUND": NEW_CONDITION_FOUND,
    "MODIFIED_CONDITIONS_TABLE": MODIFIED_CONDITIONS_TABLE,
    "CONTROL_PT_TRANSLATION": {'keys': 'controles', 'filters': 'filtros'},
    "LINK_PT_SYNTAX": {'equals': 'igual a ', 'contains': 'contém'},
    "CURRENT_CONDITIONS": "<br><br>Condições atuais dos controles não encontrados: <br> "
}