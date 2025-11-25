import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Mybooks } from './mybooks';

describe('Mybooks', () => {
  let component: Mybooks;
  let fixture: ComponentFixture<Mybooks>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Mybooks]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Mybooks);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
