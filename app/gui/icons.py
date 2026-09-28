from __future__ import annotations

import math
from PySide6.QtCore import QPointF,QRectF,Qt
from PySide6.QtGui import QColor,QIcon,QPainter,QPainterPath,QPen,QPixmap,QPolygonF


def make_icon(name:str,size:int=20,color:str="#ADBECD",accent:str="#FF1437")->QIcon:
    pix=QPixmap(size,size);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing,True);pen=QPen(QColor(color),1.7,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin);p.setPen(pen);p.setBrush(Qt.NoBrush);s=float(size);m=s*.18;cx=cy=s/2
    if name=="play":
        p.setPen(Qt.NoPen);p.setBrush(QColor(accent));p.drawRoundedRect(QRectF(m,s*.24,s-2*m,s*.52),4,4);p.setBrush(QColor("white"));p.drawPolygon(QPolygonF([QPointF(s*.43,s*.36),QPointF(s*.43,s*.64),QPointF(s*.65,s*.5)]))
    elif name=="home":
        p.drawPolyline(QPolygonF([QPointF(m,s*.48),QPointF(cx,s*.23),QPointF(s-m,s*.48)]));p.drawRoundedRect(QRectF(s*.28,s*.45,s*.44,s*.36),2,2)
    elif name=="download":
        p.drawLine(QPointF(cx,s*.2),QPointF(cx,s*.62));p.drawPolyline(QPolygonF([QPointF(s*.33,s*.48),QPointF(cx,s*.65),QPointF(s*.67,s*.48)]));p.drawLine(QPointF(s*.25,s*.78),QPointF(s*.75,s*.78))
    elif name=="playlist":
        for y in (.3,.5,.7):p.drawLine(QPointF(s*.35,s*y),QPointF(s*.78,s*y));p.drawEllipse(QPointF(s*.23,s*y),1.4,1.4)
    elif name=="channel":
        p.drawEllipse(QRectF(s*.22,s*.22,s*.24,s*.24));p.drawEllipse(QRectF(s*.57,s*.29,s*.18,s*.18));p.drawArc(QRectF(s*.15,s*.43,s*.42,s*.38),10*16,160*16);p.drawArc(QRectF(s*.5,s*.48,s*.34,s*.29),15*16,145*16)
    elif name=="history":
        p.drawEllipse(QRectF(s*.2,s*.2,s*.6,s*.6));p.drawLine(QPointF(cx,cy),QPointF(cx,s*.32));p.drawLine(QPointF(cx,cy),QPointF(s*.64,s*.57))
    elif name=="settings":
        p.drawEllipse(QRectF(s*.38,s*.38,s*.24,s*.24));p.drawEllipse(QRectF(s*.25,s*.25,s*.5,s*.5))
        for i in range(8):a=i*math.pi/4;p.drawLine(QPointF(cx+math.cos(a)*s*.27,cy+math.sin(a)*s*.27),QPointF(cx+math.cos(a)*s*.39,cy+math.sin(a)*s*.39))
    elif name=="sparkle":
        p.setPen(QPen(QColor("#47BAFF"),1.5));p.drawLine(QPointF(cx,s*.14),QPointF(cx,s*.86));p.drawLine(QPointF(s*.14,cy),QPointF(s*.86,cy));p.drawLine(QPointF(s*.3,s*.3),QPointF(s*.7,s*.7));p.drawLine(QPointF(s*.7,s*.3),QPointF(s*.3,s*.7))
    elif name=="filter":
        p.drawPolygon(QPolygonF([QPointF(s*.2,s*.25),QPointF(s*.8,s*.25),QPointF(s*.59,s*.5),QPointF(s*.59,s*.76),QPointF(s*.42,s*.84),QPointF(s*.42,s*.5)]))
    elif name=="link":
        p.drawRoundedRect(QRectF(s*.18,s*.38,s*.42,s*.25),s*.12,s*.12);p.drawRoundedRect(QRectF(s*.4,s*.28,s*.42,s*.25),s*.12,s*.12);p.drawLine(QPointF(s*.4,s*.55),QPointF(s*.62,s*.38))
    else:
        p.drawEllipse(QRectF(s*.25,s*.25,s*.5,s*.5))
    p.end();return QIcon(pix)
