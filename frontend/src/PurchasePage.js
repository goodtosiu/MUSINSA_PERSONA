import React from 'react';
import './PurchasePage.css';

const PurchasePage = ({ selectedItems, onBack, bgPath }) => {
  const totalPrice = selectedItems.reduce((sum, item) => sum + (item.price || 0), 0);

  return (
    <div className="advanced-collage-layout dark-theme">
      {/* 왼쪽: 캔버스 영역 */}
      <section className="left-canvas-area">
        <div className="canvas-header">
           <span className="outfit-badge">마이 아웃핏</span>
        </div>
        <div className="collage-canvas" 
             style={{ backgroundImage: bgPath ? `url(${bgPath})` : 'none' }}>
          {selectedItems.map((item) => (
            <div key={item.instanceId} className="canvas-item"
                 style={{ 
                   left: `${item.x}px`, 
                   top: `${item.y}px`, 
                   transform: `scale(${item.scale})`, 
                   zIndex: item.zIndex 
                 }}>
              <img src={item.img_url} alt="" draggable="false" />
            </div>
          ))}
        </div>
      </section>

      {/* 중앙 경계선 및 세로 글자 로고 */}
      <div className="center-divider-area">
        <div className="stacked-mbti-logo">
          <div className="logo-text">MUSINSA</div>
          <div className="logo-cross">×</div>
          <div className="logo-text">PERSONA</div>
        </div>
      </div>

      {/* 오른쪽: 상세 내역 */}
      <section className="right-list-area purchase-sidebar">
        <div className="top-section">
          <h2 className="sidebar-title">선택 상품</h2>
          {/* [수정] 이 영역에만 스크롤이 적용됩니다 */}
          <div className="purchase-list"> 
            {selectedItems.map((item) => (
              <div key={item.instanceId} className="purchase-item-card">
                <div className="item-img-container">
                  <img src={item.img_url} alt="" />
                </div>
                <div className="item-text-info">
                  <p className="item-name">{item.product_name}</p>
                  <p className="item-price">{item.price?.toLocaleString()}원</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 하단 버튼 섹션 (고정) */}
        <div className="action-button-group purchase-actions">
          <button className="coupon-btn" onClick={() => alert("사용 가능한 쿠폰이 없습니다.")}>
            쿠폰 사용
          </button>
          <button className="pay-btn-white" onClick={() => alert("결제 페이지로 이동합니다!")}>
            {totalPrice.toLocaleString()}원 결제하기
          </button>
          <button className="back-link-text" onClick={onBack}>
            수정하러 가기
          </button>
        </div>
      </section>
    </div>
  );
};

export default PurchasePage;