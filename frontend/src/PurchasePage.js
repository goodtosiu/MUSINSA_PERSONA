import React from 'react';
import './PurchasePage.css';

const PurchasePage = ({ selectedItems, onBack, bgPath, onBackToMain }) => {
  // 전체 합계 금액 계산
  const totalPrice = selectedItems.reduce((sum, item) => sum + item.price, 0);

  return (
    <div className="advanced-collage-layout dark-theme">
      {/* 왼쪽: 기존 캔버스 유지 (읽기 전용) */}
      <section className="left-canvas-area">
        <div className="canvas-header">
           <span className="badge">마이 아웃핏</span>
        </div>
        <div className="collage-canvas" 
             style={{ backgroundImage: bgPath ? `url(${bgPath})` : 'none', backgroundSize: 'cover', position: 'relative' }}>
          {selectedItems.map((item) => (
            <div key={item.instanceId} className="canvas-item"
                 style={{ left: `${item.x}px`, top: `${item.y}px`, transform: `scale(${item.scale})`, position: 'absolute', zIndex: item.zIndex }}>
              <img src={item.img_url} alt="" style={{ width: '150px' }} />
            </div>
          ))}
        </div>
      </section>

      {/* 오른쪽: 선택 상품 상세 정보 및 결제 (제공된 이미지 디자인) */}
      <section className="right-purchase-area">
        <div className="purchase-container">
          <h2 className="purchase-title">선택 상품</h2>
          
          <div className="selected-list">
            {selectedItems.map((item) => (
              <div key={item.instanceId} className="purchase-item-row">
                <div className="item-thumb">
                  <img src={item.img_url} alt={item.product_name} />
                </div>
                <div className="item-details">
                  <p className="brand-name">BRAND NAME</p> {/* 필요한 경우 item.brand 추가 */}
                  <p className="product-name">{item.product_name}</p>
                  <p className="product-price">{item.price?.toLocaleString()}원</p>
                </div>
              </div>
            ))}
          </div>

          <div className="center-logo">
            <p>LOOK</p>
            <p>×</p>
            <p>MBTI</p>
          </div>

          <div className="payment-section">
            <button className="coupon-btn" onClick={() => alert("사용 가능한 쿠폰이 없습니다.")}>
              쿠폰 사용
            </button>
            <button className="total-buy-btn" onClick={() => alert("결제 페이지로 이동합니다.")}>
              {totalPrice.toLocaleString()}원 결제하기
            </button>
            <button className="back-text-btn" onClick={onBack}>수정하러 가기</button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default PurchasePage;