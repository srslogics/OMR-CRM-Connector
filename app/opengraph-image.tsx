import { ImageResponse } from 'next/og';
export const alt = 'LakshyaInstitute — Student records workspace';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';
export default function Image() {
  return new ImageResponse(
    <div style={{width:'100%',height:'100%',display:'flex',flexDirection:'column',background:'#10374b',padding:'72px',color:'white',fontFamily:'sans-serif',borderTop:'12px solid #55d4be'}}>
      <div style={{display:'flex',fontSize:22,letterSpacing:5,color:'#77e0ce'}}>STUDENT DATA WORKSPACE</div>
      <div style={{display:'flex',fontSize:76,fontWeight:700,letterSpacing:-3,marginTop:70}}>LakshyaInstitute</div>
      <div style={{display:'flex',fontSize:30,color:'#c3d9e4',marginTop:24}}>Student details. Parent contacts. One workspace.</div>
      <div style={{display:'flex',gap:24,marginTop:70,fontSize:22,color:'#77e0ce'}}><span>ENTER</span><span> / </span><span>REVIEW</span><span> / </span><span>DOWNLOAD</span></div>
    </div>, size
  );
}
