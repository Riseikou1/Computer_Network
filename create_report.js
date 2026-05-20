const pptxgen = require('pptxgenjs');
const { warnIfSlideHasOverlaps, warnIfSlideElementsOutOfBounds } = require('/home/oai/skills/slides/pptxgenjs_helpers');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Computer Networks Design Project Team';
pptx.subject = 'Peer-to-Peer Messenger Design Project';
pptx.title = 'P2P Messenger Project';
pptx.company = 'Kookmin University';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Arial',
  bodyFontFace: 'Arial',
  lang: 'en-US'
};
pptx.defineLayout({ name: 'LAYOUT_WIDE', width: 13.333, height: 7.5 });

const C = {
  bg: '0F172A',
  bg2: '111827',
  white: 'F8FAFC',
  muted: 'CBD5E1',
  blue: '38BDF8',
  green: '22C55E',
  amber: 'F59E0B',
  red: 'F43F5E',
  line: '334155'
};
function title(slide, t, sub='') {
  slide.background = { color: C.bg };
  slide.addText(t, { x:0.55, y:0.35, w:12.2, h:0.45, fontFace:'Arial', fontSize:28, bold:true, color:C.white, margin:0 });
  if (sub) slide.addText(sub, { x:0.58, y:0.85, w:12, h:0.3, fontSize:12, color:C.muted, margin:0 });
  slide.addShape(pptx.ShapeType.line, { x:0.55, y:1.22, w:12.2, h:0, line:{ color:C.line, width:1 }});
}
function box(slide, text, x,y,w,h,color=C.blue, fontSize=16) {
  slide.addShape(pptx.ShapeType.roundRect, { x,y,w,h, rectRadius:0.1, fill:{color:'1E293B'}, line:{color, width:1.5} });
  slide.addText(text, { x:x+0.15, y:y+0.15, w:w-0.3, h:h-0.3, color:C.white, fontSize, fit:'shrink', valign:'mid', align:'center', margin:0.02 });
}
function bullet(slide, lines, x, y, w, h) {
  slide.addText(lines.map(s=>({text:s, options:{bullet:{indent:12}, hanging:4}})), {
    x,y,w,h,fontSize:18,color:C.white,breakLine:false,fit:'shrink',margin:0.06,
    paraSpaceAfterPt:8
  });
}
function validate(slide) {
  warnIfSlideHasOverlaps(slide, pptx, {ignoredShapeTypes:['line']});
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

let s = pptx.addSlide();
s.background = { color: C.bg };
s.addText('Peer-to-Peer Multi-User Messenger', {x:0.7,y:2.0,w:12,h:0.7,fontSize:38,bold:true,color:C.white,align:'center',margin:0});
s.addText('Computer Networks Design Project', {x:0.7,y:2.85,w:12,h:0.35,fontSize:20,color:C.blue,align:'center',margin:0});
s.addText('Login server for discovery, direct client-to-client messaging for chat', {x:1.2,y:3.5,w:11,h:0.3,fontSize:16,color:C.muted,align:'center',margin:0});
box(s,'LOGIN SERVER\nOnline user list',1.0,5.2,2.4,1.0,C.amber,16);
box(s,'CLIENT A\nlistener + sender',5.35,5.2,2.4,1.0,C.blue,16);
box(s,'CLIENT B\nlistener + sender',9.7,5.2,2.4,1.0,C.green,16);
s.addShape(pptx.ShapeType.line,{x:3.45,y:5.7,w:1.8,h:0,line:{color:C.amber,width:2,beginArrowType:'none',endArrowType:'triangle'}});
s.addShape(pptx.ShapeType.line,{x:7.8,y:5.7,w:1.8,h:0,line:{color:C.green,width:2,beginArrowType:'none',endArrowType:'triangle'}});
validate(s);

s = pptx.addSlide(); title(s,'System Requirements Covered','Only the features requested in the assignment, without building a fake startup around it.');
bullet(s,[
  'Login server stores online user ID, IP address, and port number.',
  'Client registers itself and receives the current online-user list.',
  'Online users are printed in the text UI.',
  'Client-to-client messages are sent directly, not through the login server.',
  'UI supports inviting users, ending session, and broadcasting to session users.',
  'Messages use HTTP-like headers plus body for future extensibility.'
],0.75,1.55,6.2,4.7);
box(s,'REGISTER / LIST / UNREGISTER',7.55,1.55,4.7,0.8,C.amber,17);
box(s,'INVITE / MESSAGE / END_SESSION',7.55,2.65,4.7,0.8,C.blue,17);
box(s,'Text UI commands:\nusers, invite, send, end, quit',7.55,3.75,4.7,1.1,C.green,17);
validate(s);

s = pptx.addSlide(); title(s,'Architecture','The login server only does discovery. Actual messages go peer-to-peer.');
box(s,'Login Server\nusers.json\n{id, ip, port}',5.2,1.45,2.9,1.25,C.amber,16);
box(s,'Alice Client\nTCP listener :5001\ncommand UI',0.9,4.4,2.8,1.25,C.blue,16);
box(s,'Bob Client\nTCP listener :5002\ncommand UI',5.25,4.4,2.8,1.25,C.green,16);
box(s,'Charlie Client\nTCP listener :5003\ncommand UI',9.55,4.4,2.8,1.25,C.red,16);
s.addShape(pptx.ShapeType.line,{x:2.3,y:4.35,w:3.0,h:-1.45,line:{color:C.amber,width:2,endArrowType:'triangle'}});
s.addShape(pptx.ShapeType.line,{x:6.65,y:4.35,w:0,h:-1.45,line:{color:C.amber,width:2,endArrowType:'triangle'}});
s.addShape(pptx.ShapeType.line,{x:10.95,y:4.35,w:-3.0,h:-1.45,line:{color:C.amber,width:2,endArrowType:'triangle'}});
s.addShape(pptx.ShapeType.line,{x:3.75,y:5.05,w:1.45,h:0,line:{color:C.green,width:2,endArrowType:'triangle'}});
s.addShape(pptx.ShapeType.line,{x:8.1,y:5.05,w:1.35,h:0,line:{color:C.green,width:2,endArrowType:'triangle'}});
s.addText('login / user list', {x:4.0,y:2.9,w:4.8,h:0.3,fontSize:13,color:C.muted,align:'center',margin:0});
s.addText('direct messages', {x:4.1,y:5.95,w:5.2,h:0.3,fontSize:13,color:C.muted,align:'center',margin:0});
validate(s);

s = pptx.addSlide(); title(s,'Protocol Design','A tiny HTTP-like protocol keeps messages structured and easy to extend.');
s.addText('Example peer message', {x:0.85,y:1.55,w:5.0,h:0.3,fontSize:18,bold:true,color:C.blue,margin:0});
s.addShape(pptx.ShapeType.roundRect,{x:0.85,y:2.0,w:5.3,h:2.15,fill:{color:'020617'},line:{color:C.line,width:1}});
s.addText('Command: MESSAGE\nFrom: alice\nTo: bob\nContent-Length: 9\n\nhello bob', {x:1.1,y:2.25,w:4.8,h:1.65,fontFace:'Courier New',fontSize:17,color:C.white,margin:0.03,fit:'shrink'});
bullet(s,[
  'Headers describe what the message means.',
  'Blank line separates headers from body.',
  'Content-Length makes receiving full body reliable.',
  'New features can be added later by adding headers.'
],7.0,1.75,5.2,3.0);
validate(s);

s = pptx.addSlide(); title(s,'Implementation Files','Small enough to understand, complete enough to run.');
box(s,'protocol.py\nbuild/parse messages',0.9,1.65,3.2,1.15,C.blue,16);
box(s,'login_server.py\nregister, list, unregister',5.05,1.65,3.2,1.15,C.amber,16);
box(s,'client.py\ntext UI + peer listener',9.2,1.65,3.2,1.15,C.green,16);
bullet(s,[
  'Uses Python standard library only: socket, threading, argparse, json.',
  'Each client has a background TCP server for incoming peer messages.',
  'The main thread runs the command UI.',
  'The login server writes online users to a JSON file.'
],1.25,3.45,10.8,2.5);
validate(s);

s = pptx.addSlide(); title(s,'Demo Scenario','The expected 5-minute video can follow this exact flow.');
bullet(s,[
  'Start login server on port 9000.',
  'Start Alice on port 5001 and Bob on port 5002.',
  'Run users to show online-user discovery.',
  'Alice runs invite bob.',
  'Alice runs send hello bob, Bob receives the message directly.',
  'Alice runs end, then quit.'
],0.9,1.55,6.1,4.8);
s.addShape(pptx.ShapeType.roundRect,{x:7.4,y:1.65,w:4.8,h:3.9,fill:{color:'020617'},line:{color:C.line,width:1}});
s.addText('$ python3 login_server.py --port 9000\n$ python3 client.py --id alice --listen-port 5001\n$ python3 client.py --id bob --listen-port 5002\n\n> invite bob\n> send hello bob\n> end', {x:7.7,y:1.95,w:4.25,h:3.25,fontFace:'Courier New',fontSize:15,color:C.white,fit:'shrink',margin:0.03});
validate(s);

pptx.writeFile({ fileName: '/mnt/data/messenger_project/docs/team_report.pptx' });
